"""
Regular Season Handler - Executes regular season weeks.

Dynasty-First Architecture:
- All dependencies come via context dict
- Uses UnifiedDatabaseAPI for all database operations
- No constructor injection of database/API objects
"""

from typing import Any, Dict, List
import time

from ..stage_definitions import Stage, StageType
from ..game_result_generator import generate_instant_result


class RegularSeasonHandler:
    """
    Handler for regular season stages (Week 1-18).

    Executes all games scheduled for the week and updates standings.

    Dynasty-First: All operations use dynasty_id from context.
    Dependencies come via context dict, not constructor injection.
    """

    def __init__(self):
        """Initialize the handler (no dependencies - all via context)."""
        pass

    def execute(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all games for the week.

        Args:
            stage: The current week stage
            context: Execution context with:
                - dynasty_id: Dynasty identifier
                - season: Season year
                - unified_api: UnifiedDatabaseAPI instance

        Returns:
            Dictionary with games_played, events_processed, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        dynasty_id = context.get("dynasty_id", "unknown")
        week_number = self._get_week_number(stage.stage_type)

        # DEBUG: Log query parameters
        print(f"[DEBUG RegularSeasonHandler] execute() called")
        print(f"[DEBUG RegularSeasonHandler] dynasty_id={dynasty_id}, season={season}, week={week_number}")
        print(f"[DEBUG RegularSeasonHandler] Database path: {unified_api.database_path}")

        games_played = []
        events_processed = []

        # Get all games for this week from EVENTS table (schedule is stored there)
        # The games table is for storing RESULTS after simulation
        games = unified_api.events_get_games_by_week(season, week_number)

        # DEBUG: Log what we got back
        print(f"[DEBUG RegularSeasonHandler] events_get_games_by_week returned {len(games)} games")

        if not games:
            # No games found - handle gracefully
            # Week 18: Schedule generator creates 17 weeks, so Week 18 has 0 games
            # This is expected - advance to playoffs
            if week_number == 18:
                print(f"[DEBUG RegularSeasonHandler] Week 18 has no games (17-week schedule) - advancing to playoffs")
                events_processed.append(f"Week {week_number}: Regular season complete - advancing to playoffs")
            else:
                print(f"[DEBUG RegularSeasonHandler] NO GAMES FOUND for week {week_number} - returning early")
                events_processed.append(f"Week {week_number}: No games in database")
            return {
                "games_played": games_played,
                "events_processed": events_processed,
                "week": week_number,
            }

        for game in games:
            # Skip already played games (have scores)
            if game.get("home_score") is not None:
                print(f"[DEBUG RegularSeasonHandler] Skipping already played game: {game.get('game_id')}")
                continue

            home_team_id = game.get("home_team_id")
            away_team_id = game.get("away_team_id")
            event_id = game.get("event_id")  # Use event_id to update the event
            game_id = game.get("game_id")

            # Generate instant result
            home_score, away_score = generate_instant_result(
                home_team_id,
                away_team_id,
                is_playoff=False
            )

            # Record result using UnifiedDatabaseAPI (games table for results)
            unified_api.games_insert_result({
                "game_id": game_id or f"gc_{season}_{week_number}_{home_team_id}_{away_team_id}",
                "season": season,
                "week": week_number,
                "season_type": "regular_season",
                "game_type": "regular",
                "game_date": int(time.time() * 1000),
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": home_score,
                "away_score": away_score,
                "total_plays": 0,
                "game_duration_minutes": 0,
                "overtime_periods": 0,
            })

            # Also update the event in events table to mark it as played
            if event_id:
                unified_api.events_update_game_result(event_id, home_score, away_score)

            # Update standings for both teams
            self._update_standings_for_game(
                unified_api, season,
                home_team_id, away_team_id,
                home_score, away_score
            )

            # Record game result for return
            games_played.append({
                "game_id": game_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": home_score,
                "away_score": away_score,
            })

        events_processed.append(f"Week {week_number}: {len(games_played)} games simulated")

        return {
            "games_played": games_played,
            "events_processed": events_processed,
            "week": week_number,
        }

    def _update_standings_for_game(
        self,
        unified_api,
        season: int,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int
    ) -> None:
        """Update standings for both teams after a game."""
        # Get current standings for both teams
        home_standing = unified_api.standings_get_team(home_team_id, season)
        away_standing = unified_api.standings_get_team(away_team_id, season)

        # Default values if no standing exists
        # Note: standings_get_team returns EnhancedTeamStanding object, not dict
        home_wins = home_standing.wins if home_standing else 0
        home_losses = home_standing.losses if home_standing else 0
        home_ties = home_standing.ties if home_standing else 0
        home_pf = home_standing.points_for if home_standing else 0
        home_pa = home_standing.points_against if home_standing else 0

        away_wins = away_standing.wins if away_standing else 0
        away_losses = away_standing.losses if away_standing else 0
        away_ties = away_standing.ties if away_standing else 0
        away_pf = away_standing.points_for if away_standing else 0
        away_pa = away_standing.points_against if away_standing else 0

        # Determine outcome
        if home_score > away_score:
            home_wins += 1
            away_losses += 1
        elif away_score > home_score:
            away_wins += 1
            home_losses += 1
        else:
            home_ties += 1
            away_ties += 1

        # Update points
        home_pf += home_score
        home_pa += away_score
        away_pf += away_score
        away_pa += home_score

        # Update standings via UnifiedDatabaseAPI
        unified_api.standings_update_team(
            team_id=home_team_id,
            season=season,
            wins=home_wins,
            losses=home_losses,
            ties=home_ties,
            points_for=home_pf,
            points_against=home_pa
        )

        unified_api.standings_update_team(
            team_id=away_team_id,
            season=season,
            wins=away_wins,
            losses=away_losses,
            ties=away_ties,
            points_for=away_pf,
            points_against=away_pa
        )

    def can_advance(self, stage: Stage, context: Dict[str, Any]) -> bool:
        """
        Check if all games for the week have been played.

        For simplicity, we return True after execute() runs.

        Args:
            stage: The current week stage
            context: Execution context

        Returns:
            True if all games complete (or no games scheduled)
        """
        # After execute(), week is complete
        return True

    def get_week_preview(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get preview of the week's matchups.

        Args:
            stage: The week stage
            context: Execution context

        Returns:
            Preview with matchups, standings implications, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        week_number = self._get_week_number(stage.stage_type)

        # Get games for this week from EVENTS table (schedule is stored there)
        games = unified_api.events_get_games_by_week(season, week_number)

        # Get standings for team info
        # standings_get returns nested dict: {divisions:..., conferences:..., overall:...}
        standings_data = unified_api.standings_get(season)

        # Build standings lookup from 'overall' list
        # Each item is {'team_id': int, 'standing': EnhancedTeamStanding}
        standings_lookup = {}
        for item in standings_data.get("overall", []):
            team_id = item.get("team_id")
            standing = item.get("standing")
            if team_id and standing:
                standings_lookup[team_id] = standing

        # Load team data for names/abbreviations
        from team_management.teams.team_loader import TeamDataLoader
        team_loader = TeamDataLoader()

        matchups = []
        for game in games:
            home_team_id = game.get("home_team_id")
            away_team_id = game.get("away_team_id")

            # Get standings (EnhancedTeamStanding objects or None)
            home_standing = standings_lookup.get(home_team_id)
            away_standing = standings_lookup.get(away_team_id)

            # Get team info
            home_team = team_loader.get_team_by_id(home_team_id)
            away_team = team_loader.get_team_by_id(away_team_id)

            matchups.append({
                "game_id": game.get("game_id"),
                "home_team": {
                    "id": home_team_id,
                    "name": home_team.full_name if home_team else f"Team {home_team_id}",
                    "abbreviation": home_team.abbreviation if home_team else "???",
                    "record": f"{home_standing.wins if home_standing else 0}-{home_standing.losses if home_standing else 0}",
                },
                "away_team": {
                    "id": away_team_id,
                    "name": away_team.full_name if away_team else f"Team {away_team_id}",
                    "abbreviation": away_team.abbreviation if away_team else "???",
                    "record": f"{away_standing.wins if away_standing else 0}-{away_standing.losses if away_standing else 0}",
                },
                "is_played": game.get("home_score") is not None,
                "home_score": game.get("home_score"),
                "away_score": game.get("away_score"),
            })

        return {
            "week": week_number,
            "matchups": matchups,
            "game_count": len(games),
            "played_count": sum(1 for m in matchups if m["is_played"]),
        }

    def _get_week_number(self, stage_type: StageType) -> int:
        """Extract week number from stage type."""
        # REGULAR_WEEK_1 -> 1, REGULAR_WEEK_18 -> 18
        name = stage_type.name
        if name.startswith("REGULAR_WEEK_"):
            return int(name.replace("REGULAR_WEEK_", ""))
        return 0