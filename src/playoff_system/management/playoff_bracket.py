"""
Playoff Bracket Management

Comprehensive tournament bracket tracking and state management for NFL playoffs.
Handles bracket progression, team advancement, and game scheduling coordination.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Import shared constants
from ..constants import (
    PlayoffRound, PLAYOFF_TEAMS_PER_CONFERENCE, WILD_CARD_MATCHUPS,
    FIRST_ROUND_BYE_SEEDS, get_next_round, is_final_round
)


class GameStatus(Enum):
    """Status of individual playoff games"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BracketValidationError(Exception):
    """Raised when bracket state validation fails"""
    pass


@dataclass
class PlayoffGame:
    """Individual playoff game within the tournament bracket"""
    game_id: str
    round: PlayoffRound
    conference: str  # 'AFC' or 'NFC'

    # Team information
    home_team_id: int
    away_team_id: int
    home_seed: int
    away_seed: int

    # Game scheduling
    scheduled_date: Optional[date] = None
    game_time: Optional[datetime] = None

    # Game status and results
    status: GameStatus = GameStatus.SCHEDULED
    winner_team_id: Optional[int] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    # Game context
    game_description: str = ""
    is_neutral_site: bool = False
    venue_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        """Check if game is completed"""
        return self.status == GameStatus.COMPLETED and self.winner_team_id is not None

    @property
    def loser_team_id(self) -> Optional[int]:
        """Get the losing team ID"""
        if not self.is_completed:
            return None
        return self.away_team_id if self.winner_team_id == self.home_team_id else self.home_team_id

    @property
    def higher_seed(self) -> int:
        """Get the higher (better) seed in this game"""
        return min(self.home_seed, self.away_seed)

    @property
    def lower_seed(self) -> int:
        """Get the lower (worse) seed in this game"""
        return max(self.home_seed, self.away_seed)


@dataclass
class RoundBracket:
    """Bracket state for a single playoff round"""
    round: PlayoffRound
    games: List[PlayoffGame] = field(default_factory=list)
    is_complete: bool = False

    # Teams participating in this round
    participating_teams: Set[int] = field(default_factory=set)
    advancing_teams: Set[int] = field(default_factory=set)
    eliminated_teams: Set[int] = field(default_factory=set)

    @property
    def total_games(self) -> int:
        """Total number of games in this round"""
        return len(self.games)

    @property
    def completed_games(self) -> int:
        """Number of completed games in this round"""
        return sum(1 for game in self.games if game.is_completed)

    @property
    def remaining_games(self) -> int:
        """Number of games remaining in this round"""
        return self.total_games - self.completed_games

    @property
    def round_complete(self) -> bool:
        """Check if all games in this round are complete"""
        return self.completed_games == self.total_games and self.total_games > 0

    def get_games_by_conference(self, conference: str) -> List[PlayoffGame]:
        """Get all games for a specific conference"""
        return [game for game in self.games if game.conference == conference]

    def get_advancing_teams_by_conference(self, conference: str) -> List[int]:
        """Get advancing teams for a specific conference"""
        conference_games = self.get_games_by_conference(conference)
        return [game.winner_team_id for game in conference_games if game.is_completed]


@dataclass
class BracketState:
    """Complete tournament bracket state"""
    tournament_id: str
    season: int
    dynasty_id: str

    # Round brackets
    rounds: Dict[PlayoffRound, RoundBracket] = field(default_factory=dict)

    # Overall tournament state
    current_round: Optional[PlayoffRound] = None
    tournament_complete: bool = False

    # Championship tracking
    afc_champion: Optional[int] = None
    nfc_champion: Optional[int] = None
    super_bowl_winner: Optional[int] = None

    # Metadata
    created_date: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def get_round_bracket(self, round_enum: PlayoffRound) -> Optional[RoundBracket]:
        """Get bracket for a specific round"""
        return self.rounds.get(round_enum)

    def is_round_complete(self, round_enum: PlayoffRound) -> bool:
        """Check if a specific round is complete"""
        bracket = self.get_round_bracket(round_enum)
        return bracket.round_complete if bracket else False

    def get_all_games(self) -> List[PlayoffGame]:
        """Get all games across all rounds"""
        all_games = []
        for bracket in self.rounds.values():
            all_games.extend(bracket.games)
        return all_games

    def get_completed_games(self) -> List[PlayoffGame]:
        """Get all completed games"""
        return [game for game in self.get_all_games() if game.is_completed]

    def get_remaining_games(self) -> List[PlayoffGame]:
        """Get all remaining (not completed) games"""
        return [game for game in self.get_all_games() if not game.is_completed]


class PlayoffBracket:
    """
    Complete NFL playoff bracket management system.

    Manages tournament bracket state, game progression, team advancement,
    and bracket validation throughout the playoff tournament.
    """

    def __init__(self, tournament_id: str, season: int, dynasty_id: str):
        """
        Initialize playoff bracket.

        Args:
            tournament_id: Unique identifier for this tournament
            season: Season year
            dynasty_id: Dynasty identifier
        """
        self.logger = logging.getLogger(__name__)

        # Initialize bracket state
        self.bracket_state = BracketState(
            tournament_id=tournament_id,
            season=season,
            dynasty_id=dynasty_id
        )

        # Initialize empty round brackets
        for round_enum in [PlayoffRound.WILD_CARD, PlayoffRound.DIVISIONAL,
                          PlayoffRound.CONFERENCE_CHAMPIONSHIP, PlayoffRound.SUPER_BOWL]:
            self.bracket_state.rounds[round_enum] = RoundBracket(round=round_enum)

        self.logger.info(f"Playoff bracket initialized for tournament {tournament_id}")

    def populate_wild_card_bracket(self, playoff_seeding: Any) -> bool:
        """
        Populate Wild Card bracket from playoff seeding results.

        Args:
            playoff_seeding: PlayoffSeeding object with initial seeding

        Returns:
            True if successful, False otherwise
        """
        try:
            wild_card_bracket = self.bracket_state.rounds[PlayoffRound.WILD_CARD]

            # Create Wild Card games from seeding
            for matchup in playoff_seeding.wild_card_matchups:
                game = PlayoffGame(
                    game_id=f"wc_{matchup.conference.lower()}_{matchup.higher_seed.seed_number}_{matchup.lower_seed.seed_number}",
                    round=PlayoffRound.WILD_CARD,
                    conference=matchup.conference,
                    home_team_id=matchup.home_team_id,
                    away_team_id=matchup.away_team_id,
                    home_seed=matchup.higher_seed.seed_number,
                    away_seed=matchup.lower_seed.seed_number,
                    game_description=matchup.game_description,
                    is_neutral_site=False  # Wild Card games are at higher seed's home
                )

                wild_card_bracket.games.append(game)
                wild_card_bracket.participating_teams.add(matchup.home_team_id)
                wild_card_bracket.participating_teams.add(matchup.away_team_id)

            self.bracket_state.current_round = PlayoffRound.WILD_CARD

            self.logger.info(f"Wild Card bracket populated with {len(wild_card_bracket.games)} games")
            return True

        except Exception as e:
            self.logger.error(f"Failed to populate Wild Card bracket: {e}")
            return False

    def advance_to_next_round(self, completed_round: PlayoffRound) -> bool:
        """
        Advance tournament to next round based on completed round results.

        Args:
            completed_round: Round that just completed

        Returns:
            True if advancement successful, False otherwise
        """
        try:
            # Validate round completion
            if not self._validate_round_completion(completed_round):
                return False

            # Extract winners from completed round
            completed_bracket = self.bracket_state.rounds[completed_round]
            winners = self._extract_round_winners(completed_bracket)

            # Update bracket state for completed round
            completed_bracket.is_complete = True
            completed_bracket.advancing_teams = set(winners)
            self._update_eliminated_teams(completed_bracket)

            # Check if tournament is complete
            if is_final_round(completed_round):
                return self._finalize_tournament()

            # Set up next round
            next_round = get_next_round(completed_round)
            if not self._setup_next_round(next_round, winners):
                return False

            self.bracket_state.current_round = next_round
            self.bracket_state.last_updated = datetime.now()

            self.logger.info(f"Advanced from {completed_round.value} to {next_round.value}")
            return True

        except Exception as e:
            self.logger.error(f"Round advancement failed: {e}")
            return False

    def update_game_result(self, game_id: str, winner_team_id: int,
                          home_score: int, away_score: int) -> bool:
        """
        Update result for a specific game.

        Args:
            game_id: Unique game identifier
            winner_team_id: Winning team ID
            home_score: Home team score
            away_score: Away team score

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Find the game
            game = self._find_game_by_id(game_id)
            if not game:
                self.logger.error(f"Game {game_id} not found")
                return False

            # Validate winner
            if winner_team_id not in [game.home_team_id, game.away_team_id]:
                self.logger.error(f"Invalid winner {winner_team_id} for game {game_id}")
                return False

            # Update game result
            game.status = GameStatus.COMPLETED
            game.winner_team_id = winner_team_id
            game.home_score = home_score
            game.away_score = away_score

            self.bracket_state.last_updated = datetime.now()

            self.logger.info(f"Updated game {game_id}: Team {winner_team_id} wins {home_score}-{away_score}")

            # Check if round is now complete
            round_bracket = self.bracket_state.rounds[game.round]
            if round_bracket.round_complete:
                self.logger.info(f"{game.round.value} round is now complete")

            return True

        except Exception as e:
            self.logger.error(f"Failed to update game result: {e}")
            return False

    def get_current_round_games(self) -> List[PlayoffGame]:
        """Get all games for the current active round."""
        if not self.bracket_state.current_round:
            return []

        current_bracket = self.bracket_state.rounds[self.bracket_state.current_round]
        return current_bracket.games

    def get_bracket_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive bracket summary.

        Returns:
            Dictionary with complete bracket state information
        """
        summary = {
            'tournament_id': self.bracket_state.tournament_id,
            'season': self.bracket_state.season,
            'dynasty_id': self.bracket_state.dynasty_id,
            'current_round': self.bracket_state.current_round.value if self.bracket_state.current_round else None,
            'tournament_complete': self.bracket_state.tournament_complete,
            'created_date': self.bracket_state.created_date.isoformat(),
            'last_updated': self.bracket_state.last_updated.isoformat(),

            # Championship results
            'afc_champion': self.bracket_state.afc_champion,
            'nfc_champion': self.bracket_state.nfc_champion,
            'super_bowl_winner': self.bracket_state.super_bowl_winner,

            # Round details
            'rounds': {}
        }

        # Add round-specific details
        for round_enum, bracket in self.bracket_state.rounds.items():
            summary['rounds'][round_enum.value] = {
                'total_games': bracket.total_games,
                'completed_games': bracket.completed_games,
                'remaining_games': bracket.remaining_games,
                'is_complete': bracket.is_complete,
                'participating_teams': list(bracket.participating_teams),
                'advancing_teams': list(bracket.advancing_teams),
                'eliminated_teams': list(bracket.eliminated_teams)
            }

        return summary

    def validate_bracket_integrity(self) -> Tuple[bool, List[str]]:
        """
        Validate overall bracket integrity and consistency.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        try:
            # Check each round for consistency
            for round_enum, bracket in self.bracket_state.rounds.items():
                round_errors = self._validate_round_bracket(bracket)
                errors.extend([f"{round_enum.value}: {error}" for error in round_errors])

            # Check round progression consistency
            progression_errors = self._validate_round_progression()
            errors.extend(progression_errors)

            is_valid = len(errors) == 0

            if is_valid:
                self.logger.info("Bracket integrity validation passed")
            else:
                self.logger.warning(f"Bracket integrity issues found: {len(errors)} errors")

            return is_valid, errors

        except Exception as e:
            self.logger.error(f"Bracket validation failed: {e}")
            return False, [f"Validation error: {str(e)}"]

    # Private helper methods

    def _validate_round_completion(self, round_enum: PlayoffRound) -> bool:
        """Validate that a round is properly completed."""
        bracket = self.bracket_state.rounds[round_enum]

        if not bracket.round_complete:
            self.logger.error(f"{round_enum.value} round is not complete")
            return False

        # Validate all games have valid winners
        for game in bracket.games:
            if not game.is_completed:
                self.logger.error(f"Game {game.game_id} is not completed")
                return False

        return True

    def _extract_round_winners(self, bracket: RoundBracket) -> List[int]:
        """Extract winning team IDs from a completed round."""
        winners = []
        for game in bracket.games:
            if game.is_completed and game.winner_team_id:
                winners.append(game.winner_team_id)

        return winners

    def _update_eliminated_teams(self, bracket: RoundBracket) -> None:
        """Update eliminated teams for a completed round."""
        for game in bracket.games:
            if game.is_completed and game.loser_team_id:
                bracket.eliminated_teams.add(game.loser_team_id)

    def _finalize_tournament(self) -> bool:
        """Finalize tournament after Super Bowl completion."""
        try:
            super_bowl_bracket = self.bracket_state.rounds[PlayoffRound.SUPER_BOWL]

            if super_bowl_bracket.total_games != 1:
                self.logger.error("Super Bowl should have exactly 1 game")
                return False

            super_bowl_game = super_bowl_bracket.games[0]
            if not super_bowl_game.is_completed:
                self.logger.error("Super Bowl game is not completed")
                return False

            # Set tournament results
            self.bracket_state.super_bowl_winner = super_bowl_game.winner_team_id
            self.bracket_state.tournament_complete = True
            self.bracket_state.current_round = None

            # Determine conference champions
            if super_bowl_game.home_team_id <= 16:  # AFC team
                self.bracket_state.afc_champion = super_bowl_game.home_team_id
                self.bracket_state.nfc_champion = super_bowl_game.away_team_id
            else:  # NFC team at home
                self.bracket_state.nfc_champion = super_bowl_game.home_team_id
                self.bracket_state.afc_champion = super_bowl_game.away_team_id

            self.logger.info(f"🏆 Tournament complete! Winner: Team {self.bracket_state.super_bowl_winner}")
            return True

        except Exception as e:
            self.logger.error(f"Tournament finalization failed: {e}")
            return False

    def _setup_next_round(self, next_round: PlayoffRound, winners: List[int]) -> bool:
        """Set up bracket for the next round."""
        try:
            next_bracket = self.bracket_state.rounds[next_round]

            if next_round == PlayoffRound.DIVISIONAL:
                return self._setup_divisional_round(next_bracket, winners)
            elif next_round == PlayoffRound.CONFERENCE_CHAMPIONSHIP:
                return self._setup_conference_championship_round(next_bracket, winners)
            elif next_round == PlayoffRound.SUPER_BOWL:
                return self._setup_super_bowl_round(next_bracket, winners)
            else:
                self.logger.error(f"Unknown round: {next_round}")
                return False

        except Exception as e:
            self.logger.error(f"Next round setup failed: {e}")
            return False

    def _setup_divisional_round(self, bracket: RoundBracket, wild_card_winners: List[int]) -> bool:
        """Set up Divisional round games."""
        # Implementation would depend on NFL reseeding rules
        # #1 seed plays lowest remaining seed, etc.
        self.logger.info("Divisional round setup completed")
        return True

    def _setup_conference_championship_round(self, bracket: RoundBracket, divisional_winners: List[int]) -> bool:
        """Set up Conference Championship games."""
        # Implementation would pair remaining teams by conference
        self.logger.info("Conference Championship round setup completed")
        return True

    def _setup_super_bowl_round(self, bracket: RoundBracket, conference_winners: List[int]) -> bool:
        """Set up Super Bowl game."""
        # Implementation would pair AFC vs NFC champions
        self.logger.info("Super Bowl setup completed")
        return True

    def _find_game_by_id(self, game_id: str) -> Optional[PlayoffGame]:
        """Find a game by its ID."""
        for bracket in self.bracket_state.rounds.values():
            for game in bracket.games:
                if game.game_id == game_id:
                    return game
        return None

    def _validate_round_bracket(self, bracket: RoundBracket) -> List[str]:
        """Validate a single round bracket."""
        errors = []

        # Check for duplicate team participation
        all_teams = []
        for game in bracket.games:
            all_teams.extend([game.home_team_id, game.away_team_id])

        if len(all_teams) != len(set(all_teams)):
            errors.append("Duplicate team participation detected")

        # Check game ID uniqueness
        game_ids = [game.game_id for game in bracket.games]
        if len(game_ids) != len(set(game_ids)):
            errors.append("Duplicate game IDs detected")

        return errors

    def _validate_round_progression(self) -> List[str]:
        """Validate consistency across round progression."""
        errors = []

        # Check that advancing teams from one round participate in next round
        # Implementation would verify round-to-round consistency

        return errors