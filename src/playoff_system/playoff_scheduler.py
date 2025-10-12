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
        them in the event database. Skips games that are already scheduled
        (duplicate prevention).

        Args:
            bracket: PlayoffBracket with games to schedule
            dynasty_id: Dynasty context for game_id generation

        Returns:
            List of event IDs for created events (excludes already-scheduled games)
        """
        # LOGGING: Track game event creation
        print(f"\n[PLAYOFF_SCHEDULING] _create_game_events() called")
        print(f"[PLAYOFF_SCHEDULING] Dynasty: {dynasty_id}")
        print(f"[PLAYOFF_SCHEDULING] Bracket round: {bracket.round_name if hasattr(bracket, 'round_name') else 'unknown'}")
        print(f"[PLAYOFF_SCHEDULING] Games in bracket: {len(bracket.games)}")

        event_ids = []
        skipped_duplicates = 0

        for game in bracket.games:
            # Generate game_id first to check for duplicates
            game_id = self._generate_playoff_game_id(game, dynasty_id)

            print(f"[PLAYOFF_SCHEDULING]   Processing game: {game_id}")

            # Check if this game is already scheduled (duplicate prevention)
            # IMPORTANT: Use dynasty-aware query to prevent cross-dynasty conflicts
            existing_events = self.event_db_api.get_events_by_game_id_and_dynasty(
                game_id, dynasty_id
            )

            print(f"[PLAYOFF_SCHEDULING]     Existing events for this game_id: {len(existing_events)}")

            if existing_events:
                # Game already exists - skip to prevent duplicate simulation
                print(f"[PLAYOFF_SCHEDULING]     ⚠️  SKIPPING: Game already scheduled")
                print(f"[PLAYOFF_SCHEDULING]        Existing event_id: {existing_events[0]['event_id']}")
                skipped_duplicates += 1
                # Still include the existing event_id in return list
                event_ids.append(existing_events[0]['event_id'])
                continue

            # Convert Date to datetime for GameEvent
            py_date = game.game_date.to_python_date()
            game_datetime = datetime.combine(py_date, datetime.min.time())

            # Create GameEvent
            event = GameEvent(
                away_team_id=game.away_team_id,
                home_team_id=game.home_team_id,
                game_date=game_datetime,
                week=game.week,
                dynasty_id=dynasty_id,
                season_type="playoffs",
                game_type=game.round_name,  # 'wildcard', 'divisional', 'conference', 'super_bowl'
                overtime_type="playoffs",
                season=game.season,
                game_id=game_id
            )

            # Store event and capture event ID
            print(f"[PLAYOFF_SCHEDULING]     ✅ Creating NEW event for {game_id}")
            stored_event = self.event_db_api.insert_event(event)
            print(f"[PLAYOFF_SCHEDULING]        New event_id: {stored_event.event_id}")
            event_ids.append(stored_event.event_id)

        print(f"[PLAYOFF_SCHEDULING] _create_game_events() complete:")
        print(f"[PLAYOFF_SCHEDULING]   New events created: {len(event_ids) - skipped_duplicates}")
        print(f"[PLAYOFF_SCHEDULING]   Duplicates skipped: {skipped_duplicates}")
        print(f"[PLAYOFF_SCHEDULING]   Total event_ids returned: {len(event_ids)}")

        if skipped_duplicates > 0:
            print(f"⚠️  Skipped {skipped_duplicates} already-scheduled playoff game(s)")

        return event_ids

    def _generate_playoff_game_id(
        self,
        game: PlayoffGame,
        dynasty_id: str
    ) -> str:
        """
        Generate unique playoff game identifier.

        Format: playoff_{season}_{round}_{game_number}

        Note: dynasty_id is no longer encoded in game_id since it's now
        stored as a separate column in the events table.

        Args:
            game: PlayoffGame to generate ID for
            dynasty_id: Dynasty context (kept for API compatibility but not used in ID)

        Returns:
            Unique game ID string
        """
        return f"playoff_{game.season}_{game.round_name}_{game.game_number}"

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
