"""
Playoff Handler - Executes playoff rounds.

Dynasty-First Architecture:
- All dependencies come via context dict
- Uses UnifiedDatabaseAPI for all database operations
- Uses production PlayoffSeeder for seeding
"""

from typing import Any, Dict, List
import time

from ..stage_definitions import Stage, StageType
from ..game_result_generator import generate_instant_result


class PlayoffHandler:
    """
    Handler for playoff stages (Wild Card through Super Bowl).

    Executes all games for the round and advances the bracket.

    Dynasty-First: All operations use dynasty_id from context.
    Dependencies come via context dict, not constructor injection.
    """

    # Map stage type to round name
    ROUND_NAMES = {
        StageType.WILD_CARD: "wild_card",
        StageType.DIVISIONAL: "divisional",
        StageType.CONFERENCE_CHAMPIONSHIP: "conference",
        StageType.SUPER_BOWL: "super_bowl",
    }

    # Number of games in each round
    ROUND_GAME_COUNTS = {
        "wild_card": 6,       # 3 per conference
        "divisional": 4,      # 2 per conference
        "conference": 2,      # 1 per conference
        "super_bowl": 1,
    }

    def __init__(self):
        """Initialize the handler (no dependencies - all via context)."""
        pass

    def execute(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all games for the playoff round.

        Args:
            stage: The current playoff stage
            context: Execution context with:
                - dynasty_id: Dynasty identifier
                - season: Season year
                - unified_api: UnifiedDatabaseAPI instance

        Returns:
            Dictionary with games_played, events_processed, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        round_name = self.ROUND_NAMES.get(stage.stage_type, "unknown")

        games_played = []
        events_processed = []

        # Check if games already exist for this round
        existing_games = unified_api.games_get_by_week(season, self._round_to_week(round_name), "playoffs")

        if existing_games:
            # Games already played for this round
            events_processed.append(f"{round_name.replace('_', ' ').title()} already complete")
            for game in existing_games:
                games_played.append({
                    "game_id": game.get("game_id"),
                    "home_team_id": game.get("home_team_id"),
                    "away_team_id": game.get("away_team_id"),
                    "home_score": game.get("home_score"),
                    "away_score": game.get("away_score"),
                    "round": round_name,
                })
        else:
            # Seed and simulate this round (games table requires scores, so we do both at once)
            if round_name == "wild_card":
                games_played = self._seed_and_simulate_wild_card(context)
            elif round_name == "divisional":
                games_played = self._seed_and_simulate_divisional(context)
            elif round_name == "conference":
                games_played = self._seed_and_simulate_conference(context)
            elif round_name == "super_bowl":
                games_played = self._seed_and_simulate_super_bowl(context)

            # Log round summary for visibility
            self._log_round_summary(round_name, games_played)
            events_processed.append(f"{round_name.replace('_', ' ').title()} seeded and simulated")

        events_processed.append(f"{round_name.replace('_', ' ').title()}: {len(games_played)} games completed")

        return {
            "games_played": games_played,
            "events_processed": events_processed,
            "round": round_name,
        }

    def _round_to_week(self, round_name: str) -> int:
        """Map playoff round name to week number for database queries."""
        # Week 19 = Wild Card, 20 = Divisional, 21 = Conference, 22 = Super Bowl
        mapping = {
            "wild_card": 19,
            "divisional": 20,
            "conference": 21,
            "super_bowl": 22,
        }
        return mapping.get(round_name, 19)

    def can_advance(self, stage: Stage, context: Dict[str, Any]) -> bool:
        """
        Check if all games for the round have been played.

        Args:
            stage: The current playoff stage
            context: Execution context

        Returns:
            True if all games complete
        """
        # After execute(), round is complete
        return True

    def _seed_and_simulate_wild_card(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed and simulate the Wild Card round using production PlayoffSeeder.

        Creates and simulates 6 games: 3 per conference
        - #2 vs #7
        - #3 vs #6
        - #4 vs #5

        Returns:
            List of game results
        """
        unified_api = context["unified_api"]
        season = context["season"]

        # Use production PlayoffSeeder
        from playoff_system.playoff_seeder import PlayoffSeeder

        seeder = PlayoffSeeder()

        # Get standings in production format
        standings_data = unified_api.standings_get(season)

        # Build standings dict for seeder (Dict[int, EnhancedTeamStanding])
        standings_dict = self._build_standings_dict(standings_data)

        # Calculate seeding via production seeder
        seeding = seeder.calculate_seeding(standings_dict, season=season, week=18)

        games_played = []

        # Create and simulate wild card matchups from seeding
        for conference in ["AFC", "NFC"]:
            seeds = self._get_seeds_for_conference(seeding, conference)

            if len(seeds) >= 7:
                # Higher seed is home team
                # #2 vs #7
                result = self._simulate_and_insert_game(
                    context, "wild_card",
                    home_team_id=seeds[1],  # #2 seed
                    away_team_id=seeds[6]   # #7 seed
                )
                games_played.append(result)

                # #3 vs #6
                result = self._simulate_and_insert_game(
                    context, "wild_card",
                    home_team_id=seeds[2],  # #3 seed
                    away_team_id=seeds[5]   # #6 seed
                )
                games_played.append(result)

                # #4 vs #5
                result = self._simulate_and_insert_game(
                    context, "wild_card",
                    home_team_id=seeds[3],  # #4 seed
                    away_team_id=seeds[4]   # #5 seed
                )
                games_played.append(result)

        return games_played

    def _seed_and_simulate_divisional(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed and simulate the Divisional round based on Wild Card results.

        #1 seed plays lowest remaining seed
        Highest remaining seed plays other survivor

        Returns:
            List of game results
        """
        games_played = []

        for conference in ["AFC", "NFC"]:
            # Get original seeding
            seeds = self._get_conference_seeds(conference, context)

            # Get wild card winners
            wild_card_winners = self._get_round_winners("wild_card", conference, context)

            if not wild_card_winners or len(seeds) < 1:
                continue

            # #1 seed had bye
            seed_1 = seeds[0]

            # Sort wild card winners by their original seed
            winner_seeds = []
            for winner_id in wild_card_winners:
                for i, seed_id in enumerate(seeds):
                    if seed_id == winner_id:
                        winner_seeds.append((i + 1, winner_id))  # (seed_number, team_id)
                        break

            winner_seeds.sort()  # Sort by seed number

            if len(winner_seeds) >= 3:
                # #1 plays lowest remaining seed (highest seed number)
                lowest_remaining = winner_seeds[-1][1]
                result = self._simulate_and_insert_game(
                    context, "divisional",
                    home_team_id=seed_1,
                    away_team_id=lowest_remaining
                )
                games_played.append(result)

                # Two highest remaining seeds play each other
                higher = winner_seeds[0][1]
                lower = winner_seeds[1][1]
                # Higher seed is home
                result = self._simulate_and_insert_game(
                    context, "divisional",
                    home_team_id=higher,
                    away_team_id=lower
                )
                games_played.append(result)

        return games_played

    def _seed_and_simulate_conference(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed and simulate Conference Championship games.

        Winners of Divisional round play in each conference.

        Returns:
            List of game results
        """
        games_played = []

        for conference in ["AFC", "NFC"]:
            divisional_winners = self._get_round_winners("divisional", conference, context)

            if len(divisional_winners) == 2:
                # Determine home team (higher original seed)
                seeds = self._get_conference_seeds(conference, context)
                seed_map = {team_id: i for i, team_id in enumerate(seeds)}

                team1, team2 = divisional_winners
                seed1 = seed_map.get(team1, 99)
                seed2 = seed_map.get(team2, 99)

                if seed1 < seed2:
                    home, away = team1, team2
                else:
                    home, away = team2, team1

                result = self._simulate_and_insert_game(
                    context, "conference",
                    home_team_id=home,
                    away_team_id=away
                )
                games_played.append(result)

        return games_played

    def _seed_and_simulate_super_bowl(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed and simulate the Super Bowl.

        Winners of AFC and NFC Championship games.

        Returns:
            List of game results
        """
        games_played = []

        afc_winners = self._get_round_winners("conference", "AFC", context)
        nfc_winners = self._get_round_winners("conference", "NFC", context)

        if afc_winners and nfc_winners:
            # Super Bowl home team alternates by year, but for simplicity
            # we'll just use AFC as "home"
            result = self._simulate_and_insert_game(
                context, "super_bowl",
                home_team_id=afc_winners[0],
                away_team_id=nfc_winners[0]
            )
            games_played.append(result)

        return games_played

    def _simulate_and_insert_game(
        self,
        context: Dict[str, Any],
        round_name: str,
        home_team_id: int,
        away_team_id: int
    ) -> Dict[str, Any]:
        """
        Simulate a playoff game and insert the result into the database.

        Args:
            context: Execution context with unified_api and season
            round_name: Playoff round name
            home_team_id: Home team ID
            away_team_id: Away team ID

        Returns:
            Game result dictionary
        """
        unified_api = context["unified_api"]
        season = context["season"]

        game_id = f"playoff_{season}_{round_name}_{home_team_id}_{away_team_id}"
        week = self._round_to_week(round_name)

        # Generate instant result (playoffs never tie)
        home_score, away_score = generate_instant_result(
            home_team_id,
            away_team_id,
            is_playoff=True
        )

        # Insert with actual scores (games table requires NOT NULL scores)
        unified_api.games_insert_result({
            "game_id": game_id,
            "season": season,
            "week": week,
            "season_type": "playoffs",
            "game_type": round_name,
            "game_date": int(time.time() * 1000),
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "total_plays": 0,
            "game_duration_minutes": 0,
            "overtime_periods": 0,
        })

        result = {
            "game_id": game_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "round": round_name,
        }

        # Log the game result for visibility
        self._log_game_result(result, round_name)

        return result

    def _log_game_result(self, game_result: Dict[str, Any], round_name: str) -> None:
        """Log game result in clear, readable format for testing."""
        home_id = game_result["home_team_id"]
        away_id = game_result["away_team_id"]
        home_score = game_result["home_score"]
        away_score = game_result["away_score"]

        # Get team names
        from team_management.teams.team_loader import TeamDataLoader
        team_loader = TeamDataLoader()
        home_team = team_loader.get_team_by_id(home_id)
        away_team = team_loader.get_team_by_id(away_id)

        home_name = home_team.abbreviation if home_team else f"Team {home_id}"
        away_name = away_team.abbreviation if away_team else f"Team {away_id}"

        # Determine winner
        winner = home_name if home_score > away_score else away_name

        print(f"🏈 {round_name.upper()}: {away_name} {away_score} @ {home_name} {home_score} → {winner} wins!")

    def _log_round_summary(self, round_name: str, games_played: List[Dict[str, Any]]) -> None:
        """Log summary of completed round."""
        print(f"\n{'='*60}")
        print(f"📋 {round_name.replace('_', ' ').upper()} COMPLETE - {len(games_played)} games")
        print(f"{'='*60}\n")

    def _build_standings_dict(self, standings_data: Dict[str, Any]) -> Dict:
        """
        Build standings dict for PlayoffSeeder.

        Args:
            standings_data: Dict from unified_api.standings_get() with structure:
                {
                    'divisions': {...},
                    'conferences': {...},
                    'overall': [{'team_id': int, 'standing': EnhancedTeamStanding}, ...],
                    'playoff_picture': {}
                }

        Returns:
            Dict[int, EnhancedTeamStanding] for PlayoffSeeder
        """
        standings_dict = {}

        # standings_data['overall'] is a list of {'team_id': int, 'standing': EnhancedTeamStanding}
        for item in standings_data.get('overall', []):
            team_id = item.get('team_id')
            standing = item.get('standing')
            if team_id and standing:
                standings_dict[team_id] = standing

        return standings_dict

    def _get_seeds_for_conference(self, seeding, conference: str) -> List[int]:
        """
        Extract team IDs in seed order (1-7) from PlayoffSeeding object.

        Args:
            seeding: PlayoffSeeding dataclass from PlayoffSeeder.calculate_seeding()
            conference: "AFC" or "NFC"

        Returns:
            List of team IDs in seed order [seed1_id, seed2_id, ..., seed7_id]
        """
        if conference == "AFC":
            conf_seeding = seeding.afc
        else:
            conf_seeding = seeding.nfc

        # Extract team_id from each PlayoffSeed, maintaining seed order
        return [seed.team_id for seed in conf_seeding.seeds]

    def _get_conference_seeds(self, conference: str, context: Dict[str, Any]) -> List[int]:
        """
        Get conference team IDs sorted by playoff seeding.

        Returns list of team IDs in seed order (1-7).
        """
        unified_api = context["unified_api"]
        season = context["season"]

        # Use production PlayoffSeeder
        from playoff_system.playoff_seeder import PlayoffSeeder

        seeder = PlayoffSeeder()

        # Get standings
        standings_data = unified_api.standings_get(season)

        # Build standings dict
        standings_dict = self._build_standings_dict(standings_data)

        # Calculate seeding
        seeding = seeder.calculate_seeding(standings_dict, season=season, week=18)

        return self._get_seeds_for_conference(seeding, conference)

    def _get_round_winners(
        self,
        round_name: str,
        conference: str,
        context: Dict[str, Any]
    ) -> List[int]:
        """
        Get winners from a playoff round for a conference.

        Args:
            round_name: Playoff round name
            conference: 'AFC' or 'NFC'
            context: Execution context

        Returns:
            List of winning team IDs
        """
        unified_api = context["unified_api"]
        season = context["season"]

        games = unified_api.games_get_by_week(season, self._round_to_week(round_name), "playoffs")

        # Get conference teams for filtering
        conf_team_ids = self._get_conference_team_ids(conference, context)

        winners = []
        for game in games:
            home_score = game.get("home_score")
            away_score = game.get("away_score")

            if home_score is None:
                continue  # Game not played

            home_team_id = game.get("home_team_id")
            away_team_id = game.get("away_team_id")

            # Determine winner
            if home_score > away_score:
                winner_id = home_team_id
            else:
                winner_id = away_team_id

            # Only include if winner is in this conference
            if winner_id in conf_team_ids:
                winners.append(winner_id)

        return winners

    def _get_conference_team_ids(self, conference: str, context: Dict[str, Any]) -> set:
        """Get all team IDs in a conference."""
        unified_api = context["unified_api"]
        season = context["season"]

        standings_data = unified_api.standings_get(season)

        team_ids = set()
        # Use conferences dict from standings_data
        conf_teams = standings_data.get('conferences', {}).get(conference, [])
        for item in conf_teams:
            team_id = item.get('team_id')
            if team_id:
                team_ids.add(team_id)

        return team_ids

    def get_round_preview(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get preview of the playoff round matchups.

        Args:
            stage: The playoff stage
            context: Execution context

        Returns:
            Preview with matchups, seeds, home field, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        round_name = self.ROUND_NAMES.get(stage.stage_type, "unknown")

        games = unified_api.games_get_by_week(season, self._round_to_week(round_name), "playoffs")

        # Get standings for team info
        standings_data = unified_api.standings_get(season)

        # Build standings lookup from 'overall' list
        # Each item is {'team_id': int, 'standing': EnhancedTeamStanding}
        standings_lookup = {}
        for item in standings_data.get('overall', []):
            team_id = item.get('team_id')
            standing = item.get('standing')
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

            # Get team info from team loader
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
            "round": round_name,
            "display_name": self._get_round_display_name(stage.stage_type),
            "matchups": matchups,
            "game_count": len(games),
            "played_count": sum(1 for m in matchups if m["is_played"]),
        }

    def _get_round_display_name(self, stage_type: StageType) -> str:
        """Get display name for playoff round."""
        names = {
            StageType.WILD_CARD: "Wild Card Weekend",
            StageType.DIVISIONAL: "Divisional Round",
            StageType.CONFERENCE_CHAMPIONSHIP: "Conference Championships",
            StageType.SUPER_BOWL: "Super Bowl",
        }
        return names.get(stage_type, "Unknown Round")