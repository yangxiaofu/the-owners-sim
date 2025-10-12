"""
Bracket Persistence Module

Handles persistence and reconstruction of playoff bracket state from database events.
Provides methods to check for existing rounds, load playoff events, and reconstruct
playoff state from stored game events.

Key Components:
- check_existing_round(): Check if a playoff round has scheduled games
- load_playoff_events(): Load all playoff events for a dynasty/season
- reconstruct_state(): Rebuild playoff state from database events

This module ensures playoff brackets can be persisted across sessions and
reconstructed accurately from the event database.
"""

from typing import Dict, List, Any, Optional, Callable
import json

from events.event_database_api import EventDatabaseAPI
from playoff_system.playoff_state import PlayoffState


class BracketPersistence:
    """
    Manages persistence and reconstruction of playoff bracket state.

    This class provides functionality to:
    1. Check for existing playoff games in the database
    2. Load all playoff events for a dynasty/season
    3. Reconstruct playoff state from stored events

    Attributes:
        event_db: EventDatabaseAPI instance for database operations
    """

    def __init__(self, event_db: EventDatabaseAPI):
        """
        Initialize BracketPersistence with event database API.

        Args:
            event_db: EventDatabaseAPI instance for database operations
        """
        self.event_db = event_db

    def check_existing_round(
        self,
        dynasty_id: str,
        season: int,
        round_name: str
    ) -> List[Dict[str, Any]]:
        """
        Check if a specific playoff round already has scheduled games.

        Queries the database for GAME events matching the dynasty, season,
        and round name pattern. Used to prevent duplicate game creation.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            round_name: Playoff round name (e.g., "wild_card", "divisional")

        Returns:
            List of existing event dicts for this round (empty if none exist)
        """
        # Query all GAME events for this dynasty
        all_events = self.event_db.get_events_by_dynasty(
            dynasty_id=dynasty_id,
            event_type="GAME"
        )

        # Filter for games matching this season and round
        round_prefix = f"playoff_{season}_{round_name}_"
        matching_events = []

        for event in all_events:
            # Get game_id from event data
            game_id = event.get("game_id")
            if game_id and game_id.startswith(round_prefix):
                matching_events.append(event)

        return matching_events

    def load_playoff_events(
        self,
        dynasty_id: str,
        season: int
    ) -> List[Dict[str, Any]]:
        """
        Load all playoff events for a dynasty/season.

        Retrieves all GAME events from the database that match the playoff
        pattern for the specified dynasty and season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of playoff event dicts
        """
        # Query all GAME events for this dynasty
        all_events = self.event_db.get_events_by_dynasty(
            dynasty_id=dynasty_id,
            event_type="GAME"
        )

        # Filter for playoff games in this season
        playoff_prefix = f"playoff_{season}_"
        playoff_events = []

        for event in all_events:
            # Get game_id from event data (defensive NULL check)
            game_id = event.get("game_id")
            if game_id and game_id.startswith(playoff_prefix):
                playoff_events.append(event)

        return playoff_events

    def reconstruct_state(
        self,
        playoff_events: List[Dict[str, Any]],
        detect_round_func: Callable[[str], Optional[str]],
        original_seeding: Optional['PlayoffSeeding'] = None
    ) -> PlayoffState:
        """
        Reconstruct playoff state from existing database events.

        Parses playoff game events and rebuilds the playoff bracket state,
        including completed games, winners, and current round. Uses the
        provided detect_round_func to determine which round each game belongs to.

        CRITICAL: Uses game_id (NOT event_id) for round detection to ensure
        accurate round identification.

        Args:
            playoff_events: List of playoff game events from database
            detect_round_func: Function to detect round from game_id
                              Should accept game_id string and return round name or None
            original_seeding: Original playoff seeding to restore (prevents NoneType crash)

        Returns:
            PlayoffState object with reconstructed bracket state
        """
        # Create fresh playoff state
        state = PlayoffState()

        # Restore original seeding IMMEDIATELY (prevents NoneType crash during bracket reconstruction)
        # This must happen before any bracket operations that might access state.original_seeding
        if original_seeding:
            state.original_seeding = original_seeding

        # Process each playoff event
        for event in playoff_events:
            # Parse event data
            game_id = event.get("game_id")
            if not game_id:
                continue

            # Extract JSON data from the event
            event_data = event.get("data", "{}")
            if isinstance(event_data, str):
                try:
                    event_data = json.loads(event_data)
                except json.JSONDecodeError:
                    continue

            # Extract parameters and results
            parameters = event_data.get("parameters", {})
            results = event_data.get("results")  # Note: 'results' not 'result'

            # Skip if no results (game not completed yet)
            if not results:
                continue

            # Detect round using game_id (CRITICAL BUG FIX)
            round_name = detect_round_func(game_id)
            if not round_name:
                continue

            # Extract game information
            away_team_id = parameters.get("away_team_id")
            home_team_id = parameters.get("home_team_id")
            away_score = results.get("away_score")
            home_score = results.get("home_score")

            # Validate required fields
            if away_team_id is None or home_team_id is None:
                continue
            if away_score is None or home_score is None:
                continue

            # Determine winner
            winner_id = home_team_id if home_score > away_score else away_team_id

            # Build completed game record
            completed_game = {
                "event_id": game_id,  # Use game_id as event_id for duplicate detection
                "away_team_id": away_team_id,
                "home_team_id": home_team_id,
                "away_score": away_score,
                "home_score": home_score,
                "winner_id": winner_id
            }

            # Add to state (with duplicate prevention)
            state.add_completed_game(round_name, completed_game)

        # Determine current round from state
        active_round = state.get_active_round()
        if active_round:
            state.current_round = active_round

        return state
