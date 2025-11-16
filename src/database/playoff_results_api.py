"""
Playoff Results Database API

Extracts playoff results from the events table for draft order calculation.
Provides playoff losers/winners in the format needed by DraftOrderService.
"""

import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime


class PlayoffResultsAPI:
    """
    Database API for extracting playoff results for draft order calculation.

    Queries the events table to extract playoff game results and organize them
    by round (wild card, divisional, conference championship, Super Bowl).

    Output format matches DraftOrderService.calculate_draft_order() input requirements.
    """

    # Round name constants (match PlayoffController)
    ROUND_WILD_CARD = 'wild_card'
    ROUND_DIVISIONAL = 'divisional'
    ROUND_CONFERENCE = 'conference'
    ROUND_SUPER_BOWL = 'super_bowl'

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Playoff Results API.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)

    def get_playoff_results(self, dynasty_id: str, season: int) -> Dict[str, Any]:
        """
        Extract playoff results from database in format for DraftOrderService.

        Queries events table for all playoff games and organizes losers by round.

        Args:
            dynasty_id: Dynasty identifier for data isolation
            season: Season year (e.g., 2024 for 2024-25 playoffs)

        Returns:
            Dict with keys:
                'wild_card_losers': List[int] - 6 team_ids
                'divisional_losers': List[int] - 4 team_ids
                'conference_losers': List[int] - 2 team_ids
                'super_bowl_loser': int - 1 team_id
                'super_bowl_winner': int - 1 team_id

        Raises:
            ValueError: If playoff data is incomplete or invalid
        """
        self.logger.info(f"Extracting playoff results for dynasty='{dynasty_id}', season={season}")

        # Extract losers for each round
        wild_card_losers = self._get_round_losers(dynasty_id, season, self.ROUND_WILD_CARD)
        divisional_losers = self._get_round_losers(dynasty_id, season, self.ROUND_DIVISIONAL)
        conference_losers = self._get_round_losers(dynasty_id, season, self.ROUND_CONFERENCE)

        # Extract Super Bowl winner and loser
        super_bowl_teams = self._get_super_bowl_teams(dynasty_id, season)

        # Build result dict
        results = {
            'wild_card_losers': wild_card_losers,
            'divisional_losers': divisional_losers,
            'conference_losers': conference_losers,
            'super_bowl_loser': super_bowl_teams['loser'],
            'super_bowl_winner': super_bowl_teams['winner']
        }

        # Validate results
        self._validate_playoff_results(results)

        self.logger.info(f"✅ Playoff results extracted: "
                        f"WC losers={len(wild_card_losers)}, "
                        f"DIV losers={len(divisional_losers)}, "
                        f"CONF losers={len(conference_losers)}, "
                        f"SB winner={super_bowl_teams['winner']}")

        return results

    def _get_round_losers(self, dynasty_id: str, season: int, round_name: str) -> List[int]:
        """
        Extract losing team_ids from a specific playoff round.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            round_name: Round name ('wild_card', 'divisional', 'conference')

        Returns:
            List of team_ids that lost in this round
        """
        losers = []

        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            # Query events table for playoff games in this round
            # Events are stored with event_type='GAME' and data contains game details
            query = '''
                SELECT event_id, data
                FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'GAME'
            '''

            cursor = conn.execute(query, (dynasty_id,))
            events = cursor.fetchall()

            # Process each event to find games matching this round
            for event in events:
                data = json.loads(event['data'])

                # Check if this is a playoff game for the correct round
                parameters = data.get('parameters', {})
                results = data.get('results', {})

                # Filter by season_type='playoffs' and game_type matching round
                season_type = parameters.get('season_type')
                game_type = parameters.get('game_type')
                event_season = parameters.get('season')

                # Skip if not playoff game or wrong season
                if season_type != 'playoffs' or event_season != season:
                    continue

                # Map game_type to round_name
                # game_type can be: 'wildcard', 'divisional', 'conference', 'super_bowl'
                # round_name uses: 'wild_card', 'divisional', 'conference', 'super_bowl'
                if game_type == 'wildcard' and round_name != 'wild_card':
                    continue
                if game_type != 'wildcard' and game_type != round_name:
                    continue

                # Extract teams and winner
                away_team_id = parameters.get('away_team_id')
                home_team_id = parameters.get('home_team_id')
                winner_team_id = results.get('winner_team_id') or results.get('winner_id')

                if not all([away_team_id, home_team_id, winner_team_id]):
                    self.logger.warning(f"Incomplete game data in event {event['event_id']}")
                    continue

                # Determine loser
                if winner_team_id == away_team_id:
                    loser_team_id = home_team_id
                elif winner_team_id == home_team_id:
                    loser_team_id = away_team_id
                else:
                    self.logger.error(f"Winner {winner_team_id} not in game (away={away_team_id}, home={home_team_id})")
                    continue

                losers.append(loser_team_id)

        self.logger.debug(f"Round {round_name}: {len(losers)} losers found")
        return losers

    def _get_super_bowl_teams(self, dynasty_id: str, season: int) -> Dict[str, int]:
        """
        Extract Super Bowl winner and loser.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict with keys 'winner' and 'loser' (both team_ids)

        Raises:
            ValueError: If Super Bowl game not found or incomplete
        """
        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            # Query for Super Bowl game
            query = '''
                SELECT event_id, data
                FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'GAME'
            '''

            cursor = conn.execute(query, (dynasty_id,))
            events = cursor.fetchall()

            # Find Super Bowl game
            for event in events:
                data = json.loads(event['data'])
                parameters = data.get('parameters', {})
                results = data.get('results', {})

                # Check if this is the Super Bowl
                season_type = parameters.get('season_type')
                game_type = parameters.get('game_type')
                event_season = parameters.get('season')

                if (season_type == 'playoffs' and
                    game_type == 'super_bowl' and
                    event_season == season):

                    # Extract teams and winner
                    away_team_id = parameters.get('away_team_id')
                    home_team_id = parameters.get('home_team_id')
                    winner_team_id = results.get('winner_team_id') or results.get('winner_id')

                    if not all([away_team_id, home_team_id, winner_team_id]):
                        raise ValueError(f"Incomplete Super Bowl data in event {event['event_id']}")

                    # Determine loser
                    if winner_team_id == away_team_id:
                        loser_team_id = home_team_id
                    elif winner_team_id == home_team_id:
                        loser_team_id = away_team_id
                    else:
                        raise ValueError(
                            f"Super Bowl winner {winner_team_id} not in game "
                            f"(away={away_team_id}, home={home_team_id})"
                        )

                    return {
                        'winner': winner_team_id,
                        'loser': loser_team_id
                    }

        # Super Bowl not found
        raise ValueError(
            f"Super Bowl not found for dynasty='{dynasty_id}', season={season}. "
            f"Playoffs may be incomplete."
        )

    def _validate_playoff_results(self, results: Dict[str, Any]) -> None:
        """
        Validate playoff results structure and team counts.

        Args:
            results: Playoff results dict from get_playoff_results()

        Raises:
            ValueError: If results are invalid or incomplete
        """
        # Check required keys
        required_keys = ['wild_card_losers', 'divisional_losers', 'conference_losers',
                        'super_bowl_loser', 'super_bowl_winner']
        missing_keys = [key for key in required_keys if key not in results]
        if missing_keys:
            raise ValueError(f"Missing required keys in playoff results: {missing_keys}")

        # Validate team counts (NFL playoff structure)
        if len(results['wild_card_losers']) != 6:
            raise ValueError(
                f"Expected 6 wild card losers, got {len(results['wild_card_losers'])}"
            )

        if len(results['divisional_losers']) != 4:
            raise ValueError(
                f"Expected 4 divisional losers, got {len(results['divisional_losers'])}"
            )

        if len(results['conference_losers']) != 2:
            raise ValueError(
                f"Expected 2 conference losers, got {len(results['conference_losers'])}"
            )

        # Validate Super Bowl teams are integers
        if not isinstance(results['super_bowl_loser'], int):
            raise ValueError("super_bowl_loser must be an integer team_id")

        if not isinstance(results['super_bowl_winner'], int):
            raise ValueError("super_bowl_winner must be an integer team_id")

        # Check for duplicate teams across all playoff categories
        all_playoff_teams = (
            results['wild_card_losers'] +
            results['divisional_losers'] +
            results['conference_losers'] +
            [results['super_bowl_loser']] +
            [results['super_bowl_winner']]
        )

        if len(all_playoff_teams) != len(set(all_playoff_teams)):
            raise ValueError("Duplicate teams found in playoff results")

        # Should have exactly 14 playoff teams total (6+4+2+1+1)
        if len(all_playoff_teams) != 14:
            raise ValueError(
                f"Expected 14 total playoff teams, got {len(all_playoff_teams)}"
            )

        self.logger.debug("✅ Playoff results validation passed")

    def playoffs_complete(self, dynasty_id: str, season: int) -> bool:
        """
        Check if playoffs are complete for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if Super Bowl has been played, False otherwise
        """
        try:
            self._get_super_bowl_teams(dynasty_id, season)
            return True
        except ValueError:
            return False
