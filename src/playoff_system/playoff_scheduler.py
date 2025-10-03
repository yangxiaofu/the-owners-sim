"""
Playoff Scheduler

Creates GameEvent objects for playoff games dynamically.
Handles progressive bracket scheduling as results come in.
"""

from typing import List, Dict, Any
from datetime import datetime

from .playoff_manager import PlayoffManager
from .bracket_models import PlayoffBracket, PlayoffGame
from .seeding_models import PlayoffSeeding
from calendar.date_models import Date
from shared.game_result import GameResult
from events.game_event import GameEvent
from events.event_database_api import EventDatabaseAPI


class PlayoffScheduler:
    """
    Creates and schedules playoff GameEvent objects.

    This class handles the side effects of playoff scheduling:
    - Creating GameEvent objects from bracket data
    - Storing events in EventDatabaseAPI
    - Progressive scheduling (schedule next round after results are in)

    Works in conjunction with PlayoffManager:
    - PlayoffManager: Pure logic (generates brackets)
    - PlayoffScheduler: Side effects (creates events)
    """

    def __init__(
        self,
        event_db_api: EventDatabaseAPI,
        playoff_manager: PlayoffManager
    ):
        """
        Initialize playoff scheduler.

        Args:
            event_db_api: For storing game events
            playoff_manager: For determining matchups
        """
        self.event_db_api = event_db_api
        self.playoff_manager = playoff_manager

    def schedule_wild_card_round(
        self,
        seeding: PlayoffSeeding,
        start_date: Date,
        season: int,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Schedule wild card games (known immediately from seeding).

        This is called when playoffs begin. Wild card matchups are known
        from the final regular season seeding, so all 6 games can be
        scheduled immediately.

        Args:
            seeding: Complete playoff seeding from PlayoffSeeder
            start_date: First wild card game date
            season: Season year
            dynasty_id: Dynasty context

        Returns:
            {
                'bracket': PlayoffBracket,
                'event_ids': List[str],
                'games_scheduled': 6
            }
        """
        # 1. Generate wild card bracket using PlayoffManager
        bracket = self.playoff_manager.generate_wild_card_bracket(
            seeding=seeding,
            start_date=start_date,
            season=season
        )

        # 2. Create GameEvent objects for all wild card games
        event_ids = self._create_game_events(bracket, dynasty_id)

        return {
            'bracket': bracket,
            'event_ids': event_ids,
            'games_scheduled': len(event_ids),
            'round_name': 'wild_card',
            'start_date': start_date
        }

    def schedule_next_round(
        self,
        completed_results: List[GameResult],
        current_round: str,
        original_seeding: PlayoffSeeding,
        start_date: Date,
        season: int,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Schedule next playoff round based on completed results.

        This is called after a round completes. Uses results to determine
        the next round's matchups, then schedules those games.

        Progressive flow:
        - Wild card completes → Schedule divisional
        - Divisional completes → Schedule conference championships
        - Conference championships complete → Schedule Super Bowl

        Args:
            completed_results: Results from just-completed round
            current_round: 'wild_card', 'divisional', or 'conference'
            original_seeding: Original playoff seeding (for re-seeding logic)
            start_date: When next round starts
            season: Season year
            dynasty_id: Dynasty context

        Returns:
            {
                'bracket': PlayoffBracket,
                'event_ids': List[str],
                'games_scheduled': int,
                'round_name': str
            }

        Raises:
            ValueError: If current_round is unknown
        """
        # Determine next round and generate bracket
        if current_round == 'wild_card':
            bracket = self.playoff_manager.generate_divisional_bracket(
                wild_card_results=completed_results,
                original_seeding=original_seeding,
                start_date=start_date,
                season=season
            )
            next_round = 'divisional'

        elif current_round == 'divisional':
            bracket = self.playoff_manager.generate_conference_championship_bracket(
                divisional_results=completed_results,
                start_date=start_date,
                season=season
            )
            next_round = 'conference'

        elif current_round == 'conference':
            bracket = self.playoff_manager.generate_super_bowl_bracket(
                conference_results=completed_results,
                start_date=start_date,
                season=season
            )
            next_round = 'super_bowl'

        else:
            raise ValueError(
                f"Unknown round: {current_round}. "
                f"Expected 'wild_card', 'divisional', or 'conference'"
            )

        # Create GameEvent objects for next round
        event_ids = self._create_game_events(bracket, dynasty_id)

        return {
            'bracket': bracket,
            'event_ids': event_ids,
            'games_scheduled': len(event_ids),
            'round_name': next_round,
            'start_date': start_date
        }

    def _create_game_events(
        self,
        bracket: PlayoffBracket,
        dynasty_id: str
    ) -> List[str]:
        """
        Create GameEvent objects from bracket, return event IDs.

        Converts PlayoffGame objects to GameEvent objects and stores
        them in the event database.

        Args:
            bracket: PlayoffBracket with games to schedule
            dynasty_id: Dynasty context for game_id generation

        Returns:
            List of event IDs for created events
        """
        event_ids = []

        for game in bracket.games:
            # Convert Date to datetime for GameEvent
            py_date = game.game_date.to_python_date()
            game_datetime = datetime.combine(py_date, datetime.min.time())

            # Create GameEvent
            event = GameEvent(
                away_team_id=game.away_team_id,
                home_team_id=game.home_team_id,
                game_date=game_datetime,
                week=game.week,
                season_type="playoffs",
                overtime_type="playoffs",
                season=game.season,
                game_id=self._generate_playoff_game_id(game, dynasty_id)
            )

            # Store event and capture event ID
            event_id = self.event_db_api.store_event(event)
            event_ids.append(event_id)

        return event_ids

    def _generate_playoff_game_id(
        self,
        game: PlayoffGame,
        dynasty_id: str
    ) -> str:
        """
        Generate unique playoff game identifier.

        Format: playoff_{dynasty_id}_{season}_{round}_{game_number}

        Args:
            game: PlayoffGame to generate ID for
            dynasty_id: Dynasty context

        Returns:
            Unique game ID string
        """
        return f"playoff_{dynasty_id}_{game.season}_{game.round_name}_{game.game_number}"

    def get_scheduled_round_info(
        self,
        dynasty_id: str,
        season: int,
        round_name: str
    ) -> Dict[str, Any]:
        """
        Get information about a scheduled playoff round.

        Retrieves events from database for a specific round.

        Args:
            dynasty_id: Dynasty context
            season: Season year
            round_name: 'wild_card', 'divisional', 'conference', 'super_bowl'

        Returns:
            {
                'round_name': str,
                'games': List[GameEvent],
                'game_count': int
            }
        """
        # Query events for this round
        # This would require EventDatabaseAPI to support filtering by game_id pattern
        # For now, return placeholder structure

        return {
            'round_name': round_name,
            'games': [],  # Would retrieve from database
            'game_count': 0
        }
