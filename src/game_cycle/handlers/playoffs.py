"""
Playoff Handler - Executes playoff rounds.

Dynasty-First Architecture:
- All dependencies come via context dict
- Uses UnifiedDatabaseAPI for all database operations
- Uses production PlayoffSeeder for seeding
"""

from typing import Any, Dict, List
import time
import random
import sqlite3
import json

from ..stage_definitions import Stage, StageType
from ..game_result_generator import generate_instant_result
from ..models.injury_models import Injury
from ..services.mock_stats_generator import MockStatsGenerator
from ..services.game_simulator_service import GameSimulatorService, SimulationMode
from ..services.awards_service import AwardsService


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

        Uses pre-seeded matchups from playoff_bracket table if available.
        If not seeded, falls back to seed-and-simulate in one step.

        Args:
            stage: The current playoff stage
            context: Execution context with:
                - dynasty_id: Dynasty identifier
                - season: Season year
                - unified_api: UnifiedDatabaseAPI instance
                - db_path: Database path

        Returns:
            Dictionary with games_played, events_processed, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        round_name = self.ROUND_NAMES.get(stage.stage_type, "unknown")

        games_played = []
        events_processed = []

        # First, check if bracket has pre-seeded matchups
        bracket_matchups = self._get_bracket_matchups(round_name, context)

        # If no seeded matchups exist, seed them now (fallback for legacy databases)
        if not bracket_matchups:
            print(f"[PlayoffHandler] No seeded matchups for {round_name}, seeding now...")
            seed_result = self.seed_bracket(stage, context)
            bracket_matchups = self._get_bracket_matchups(round_name, context)

        if bracket_matchups:
            # Check if all games are already played (winner is set)
            pending_matchups = [m for m in bracket_matchups if m.get('winner') is None]

            if not pending_matchups:
                # All games already played
                events_processed.append(f"{round_name.replace('_', ' ').title()} already complete")
                for matchup in bracket_matchups:
                    games_played.append({
                        "game_id": f"playoff_{season}_{round_name}_{matchup['higher_seed']}_{matchup['lower_seed']}",
                        "home_team_id": matchup['higher_seed'],
                        "away_team_id": matchup['lower_seed'],
                        "home_score": matchup['home_score'],
                        "away_score": matchup['away_score'],
                        "round": round_name,
                    })
            else:
                # Simulate pending games from pre-seeded bracket
                games_played = self._simulate_bracket_matchups(pending_matchups, context, round_name)
                self._log_round_summary(round_name, games_played)
                events_processed.append(f"{round_name.replace('_', ' ').title()} simulated")
        else:
            # No pre-seeded bracket - use legacy seed-and-simulate approach
            # This maintains backwards compatibility
            existing_games = unified_api.games_get_by_week(season, self._round_to_week(round_name), "playoffs")

            if existing_games:
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
                # Seed and simulate together (legacy path)
                if round_name == "wild_card":
                    games_played = self._seed_and_simulate_wild_card(context)
                elif round_name == "divisional":
                    games_played = self._seed_and_simulate_divisional(context)
                elif round_name == "conference":
                    games_played = self._seed_and_simulate_conference(context)
                elif round_name == "super_bowl":
                    games_played = self._seed_and_simulate_super_bowl(context)

                self._log_round_summary(round_name, games_played)
                events_processed.append(f"{round_name.replace('_', ' ').title()} seeded and simulated")

        events_processed.append(f"{round_name.replace('_', ' ').title()}: {len(games_played)} games completed")

        # Update standings with playoff achievement flags
        if games_played:
            self._update_standings_playoff_flags(context, round_name, games_played)

        # After Super Bowl, calculate MVP and season awards
        super_bowl_result = None
        season_awards = None
        if round_name == "super_bowl" and games_played:
            super_bowl_game = games_played[0]  # Super Bowl is always a single game
            super_bowl_result, season_awards = self._calculate_end_of_season_awards(
                context, super_bowl_game
            )
            events_processed.append("Super Bowl MVP calculated")
            events_processed.append(f"Super Bowl MVP: {super_bowl_result.get('mvp', {}).get('player_name', 'Unknown')}")

        return {
            "games_played": games_played,
            "events_processed": events_processed,
            "round": round_name,
            "super_bowl_result": super_bowl_result,
            "season_awards": season_awards,
        }

    def _simulate_bracket_matchups(
        self,
        matchups: List[Dict[str, Any]],
        context: Dict[str, Any],
        round_name: str
    ) -> List[Dict[str, Any]]:
        """
        Simulate games from pre-seeded bracket matchups.

        Updates playoff_bracket with results and inserts into games table.

        Args:
            matchups: List of matchup dicts from playoff_bracket
            context: Execution context
            round_name: Playoff round name

        Returns:
            List of game results
        """
        unified_api = context["unified_api"]
        dynasty_id = context["dynasty_id"]
        season = context["season"]
        db_path = context.get("db_path") or unified_api.database_path
        games_played = []

        # Use GameSimulatorService with FULL mode for realistic play-by-play
        # Default to FULL for playoffs (can be overridden via context)
        mode_str = context.get("simulation_mode", "full")
        simulation_mode = SimulationMode.FULL if mode_str == "full" else SimulationMode.INSTANT
        game_simulator = GameSimulatorService(db_path, dynasty_id)

        # Extract progress callback for UI updates
        progress_callback = context.get("progress_callback")
        total_games = len(matchups)

        for game_num, matchup in enumerate(matchups, start=1):
            home_team_id = matchup['higher_seed']
            away_team_id = matchup['lower_seed']
            conference = matchup['conference']
            game_number = matchup['game_number']

            # Generate game_id and week for this playoff game
            game_id = f"playoff_{season}_{round_name}_{home_team_id}_{away_team_id}"
            week = self._round_to_week(round_name)

            # Use GameSimulatorService for FULL play-by-play simulation
            sim_result = game_simulator.simulate_game(
                game_id=game_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                mode=simulation_mode,
                season=season,
                week=week,
                is_playoff=True  # Ensures season_type='playoffs' and playoff OT rules
            )

            home_score = sim_result.home_score
            away_score = sim_result.away_score
            winner = home_team_id if home_score > away_score else away_team_id

            # Update playoff_bracket with result
            self._update_bracket_result(
                context, round_name, conference, game_number,
                home_score, away_score, winner
            )

            # Insert into games table for stats/history
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
                "total_plays": sim_result.total_plays,
                "game_duration_minutes": sim_result.game_duration_minutes,
                "overtime_periods": sim_result.overtime_periods,
            })

            # Insert player stats from simulation (already in correct format)
            if sim_result.player_stats:
                stats_count = unified_api.stats_insert_game_stats(
                    game_id=game_id,
                    season=season,
                    week=week,
                    season_type="playoffs",
                    player_stats=sim_result.player_stats
                )
                print(f"[PlayoffHandler] Inserted {stats_count} player stats for {game_id}")

            # Persist box scores (team stats + player stats aggregation)
            self._persist_box_scores(
                context, game_id, home_team_id, away_team_id, sim_result.player_stats,
                home_team_stats=sim_result.home_team_stats,
                away_team_stats=sim_result.away_team_stats
            )

            # Persist play-by-play data (if drives available from FULL simulation)
            if hasattr(sim_result, 'drives') and sim_result.drives:
                try:
                    from ..database.play_by_play_api import PlayByPlayAPI
                    pbp_api = PlayByPlayAPI(db_path)
                    drive_count = pbp_api.insert_drives_batch(dynasty_id, game_id, sim_result.drives)
                    play_count = pbp_api.insert_plays_batch(
                        dynasty_id, game_id, sim_result.drives,
                        home_team_id=home_team_id, away_team_id=away_team_id
                    )
                    print(f"[PlayoffHandler] Persisted {drive_count} drives, {play_count} plays for {game_id}")
                except Exception as e:
                    print(f"[PlayoffHandler] Failed to persist play-by-play for {game_id}: {e}")

            # Use injuries from simulation result (FULL mode generates injuries)
            game_injuries = [
                {"player_id": inj.player_id, "injury_type": inj.injury_type, "weeks_out": inj.weeks_out}
                for inj in sim_result.injuries
            ] if sim_result.injuries else []

            # Store game result with drives for play-by-play display
            result = {
                "game_id": game_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": home_score,
                "away_score": away_score,
                "round": round_name,
                "injuries": game_injuries,
                "drives": sim_result.drives,  # Play-by-play data (FULL mode)
                "game_result": sim_result,  # Full result for UI access (key must match StageView expectation)
            }

            self._log_game_result(result, round_name)

            # Generate media headline for this playoff game
            self._generate_playoff_headline(context, result, round_name, sim_result)

            # Generate social media posts for playoff game (Milestone 14)
            try:
                self._generate_playoff_social_posts(
                    db_path=db_path,
                    dynasty_id=dynasty_id,
                    season=season,
                    week=week,
                    round_name=round_name,
                    game_id=game_id,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_score=home_score,
                    away_score=away_score,
                    sim_result=sim_result
                )
            except Exception as e:
                print(f"[PlayoffHandler] SOCIAL POST GENERATION FAILED for {game_id}: {e}")
                # Don't fail the whole playoff simulation

            # Call progress callback if provided (for UI updates)
            if progress_callback:
                from team_management.teams.team_loader import get_team_by_id
                away_team = get_team_by_id(away_team_id)
                home_team = get_team_by_id(home_team_id)
                away_abbr = away_team.abbreviation if away_team else f"T{away_team_id}"
                home_abbr = home_team.abbreviation if home_team else f"T{home_team_id}"
                round_display = round_name.replace('_', ' ').title()
                message = f"{round_display}: {away_abbr} {away_score} @ {home_abbr} {home_score}"
                try:
                    progress_callback(game_num, total_games, message)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Progress callback failed: %s", e)

            games_played.append(result)

        return games_played

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

    def _generate_and_insert_game_stats(
        self,
        context: Dict[str, Any],
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        round_name: str
    ) -> List[Dict[str, Any]]:
        """
        Generate and insert player stats for a playoff game.

        Uses MockStatsGenerator to create realistic player stats and inserts
        them into the player_game_stats table with season_type='playoffs'.

        Args:
            context: Execution context with unified_api, dynasty_id, season
            game_id: Unique game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_score: Final home score
            away_score: Final away score
            round_name: Playoff round name

        Returns:
            List of player stats dicts (for box score aggregation)
        """
        unified_api = context["unified_api"]
        dynasty_id = context["dynasty_id"]
        season = context["season"]
        db_path = context.get("db_path") or unified_api.database_path
        week = self._round_to_week(round_name)

        try:
            # Generate mock stats for both teams
            stats_generator = MockStatsGenerator(db_path, dynasty_id, season)
            mock_result = stats_generator.generate(
                game_id=game_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_score=home_score,
                away_score=away_score,
                week=week
            )

            # Insert player stats with season_type='playoffs'
            if mock_result.player_stats:
                stats_count = unified_api.stats_insert_game_stats(
                    game_id=game_id,
                    season=season,
                    week=week,
                    season_type="playoffs",
                    player_stats=mock_result.player_stats
                )
                print(f"[PlayoffHandler] Inserted {stats_count} player stats for playoff game {game_id}")
                return mock_result.player_stats

        except Exception as e:
            print(f"[PlayoffHandler] Failed to generate/insert stats for {game_id}: {e}")

        return []

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

    def _calculate_end_of_season_awards(
        self,
        context: Dict[str, Any],
        super_bowl_game: Dict[str, Any]
    ) -> tuple:
        """
        Calculate Super Bowl MVP and season awards after Super Bowl.

        This is called immediately after Super Bowl simulation to:
        1. Calculate and store Super Bowl MVP
        2. Calculate and store all season awards (MVP, OPOY, DPOY, etc.)

        Args:
            context: Execution context with dynasty_id, season, db_path
            super_bowl_game: The Super Bowl game result dict

        Returns:
            Tuple of (super_bowl_result dict, season_awards dict)
        """
        dynasty_id = context["dynasty_id"]
        season = context["season"]
        unified_api = context["unified_api"]
        db_path = context.get("db_path") or unified_api.database_path

        game_id = super_bowl_game.get("game_id", "")
        home_team_id = super_bowl_game.get("home_team_id")
        away_team_id = super_bowl_game.get("away_team_id")
        home_score = super_bowl_game.get("home_score", 0)
        away_score = super_bowl_game.get("away_score", 0)

        # Determine winner
        winning_team_id = home_team_id if home_score > away_score else away_team_id

        # Initialize AwardsService
        awards_service = AwardsService(db_path, dynasty_id, season)

        # Calculate Super Bowl MVP
        mvp_result = awards_service.calculate_super_bowl_mvp(game_id, winning_team_id)
        mvp_data = None
        if mvp_result:
            # Store in database
            awards_service.awards_api.insert_super_bowl_mvp(
                dynasty_id=dynasty_id,
                season=season,
                game_id=game_id,
                player_id=mvp_result.player_id,
                player_name=mvp_result.player_name,
                team_id=mvp_result.team_id,
                position=mvp_result.position,
                winning_team=mvp_result.winning_team,
                stat_line=mvp_result.stat_line,
                mvp_score=mvp_result.mvp_score,
            )
            mvp_data = mvp_result.to_dict()
            print(f"[PlayoffHandler] Super Bowl MVP: {mvp_result.player_name}")

        # Build super_bowl_result
        super_bowl_result = {
            "game_id": game_id,
            "winner_team_id": winning_team_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "mvp": mvp_data,
        }

        # DISABLED: Season awards calculation moved to OffseasonHandler._execute_honors()
        # PlayoffHandler runs immediately after Super Bowl, BEFORE stats are aggregated
        # into season grades. The EligibilityChecker requires player_season_grades table
        # to be populated, which only happens in honors stage.
        #
        # Separation of concerns:
        # - PlayoffHandler: Calculate Super Bowl MVP (uses raw game stats - works fine)
        # - OffseasonHandler: Calculate season awards (after stats aggregation - correct)
        #
        # Previously this would log "No candidates found" because player_season_grades
        # table was empty. Now awards are calculated in the correct place.
        season_awards = {}
        print(f"[PlayoffHandler] Season awards will be calculated in OFFSEASON_HONORS stage")

        return super_bowl_result, season_awards

    def _simulate_and_insert_game(
        self,
        context: Dict[str, Any],
        round_name: str,
        home_team_id: int,
        away_team_id: int
    ) -> Dict[str, Any]:
        """
        Simulate a playoff game and insert the result into the database.

        Uses GameSimulatorService with FULL mode for realistic play-by-play.

        Args:
            context: Execution context with unified_api and season
            round_name: Playoff round name
            home_team_id: Home team ID
            away_team_id: Away team ID

        Returns:
            Game result dictionary
        """
        unified_api = context["unified_api"]
        dynasty_id = context["dynasty_id"]
        season = context["season"]
        db_path = context.get("db_path") or unified_api.database_path

        game_id = f"playoff_{season}_{round_name}_{home_team_id}_{away_team_id}"
        week = self._round_to_week(round_name)

        # Use GameSimulatorService with FULL mode for realistic play-by-play
        mode_str = context.get("simulation_mode", "full")
        simulation_mode = SimulationMode.FULL if mode_str == "full" else SimulationMode.INSTANT
        game_simulator = GameSimulatorService(db_path, dynasty_id)

        sim_result = game_simulator.simulate_game(
            game_id=game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            mode=simulation_mode,
            season=season,
            week=week,
            is_playoff=True  # Ensures season_type='playoffs' and playoff OT rules
        )

        home_score = sim_result.home_score
        away_score = sim_result.away_score

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
            "total_plays": sim_result.total_plays,
            "game_duration_minutes": sim_result.game_duration_minutes,
            "overtime_periods": sim_result.overtime_periods,
        })

        # Insert player stats from simulation (already in correct format)
        player_stats = sim_result.player_stats
        if player_stats:
            stats_count = unified_api.stats_insert_game_stats(
                game_id=game_id,
                season=season,
                week=week,
                season_type="playoffs",
                player_stats=player_stats
            )
            print(f"[PlayoffHandler] Inserted {stats_count} player stats for {game_id}")

        # Persist box scores (team stats + player stats aggregation)
        self._persist_box_scores(
            context, game_id, home_team_id, away_team_id, player_stats,
            home_team_stats=sim_result.home_team_stats,
            away_team_stats=sim_result.away_team_stats
        )

        # Persist play-by-play data (if drives available from FULL simulation)
        if hasattr(sim_result, 'drives') and sim_result.drives:
            try:
                from ..database.play_by_play_api import PlayByPlayAPI
                pbp_api = PlayByPlayAPI(db_path)
                drive_count = pbp_api.insert_drives_batch(dynasty_id, game_id, sim_result.drives)
                play_count = pbp_api.insert_plays_batch(
                    dynasty_id, game_id, sim_result.drives,
                    home_team_id=home_team_id, away_team_id=away_team_id
                )
                print(f"[PlayoffHandler] Persisted {drive_count} drives, {play_count} plays for {game_id}")
            except Exception as e:
                print(f"[PlayoffHandler] Failed to persist play-by-play for {game_id}: {e}")

        # Use injuries from simulation result (FULL mode generates injuries)
        game_injuries = [
            {"player_id": inj.player_id, "injury_type": inj.injury_type, "weeks_out": inj.weeks_out}
            for inj in sim_result.injuries
        ] if sim_result.injuries else []

        # Update head-to-head record for playoff game (Milestone 11, Tollgate 2)
        dynasty_id = context.get("dynasty_id")
        if dynasty_id:
            from ..database.connection import GameCycleDatabase
            from ..database.head_to_head_api import HeadToHeadAPI
            gc_db = GameCycleDatabase()
            h2h_api = HeadToHeadAPI(gc_db)
            h2h_api.update_after_game(
                dynasty_id=dynasty_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_score=home_score,
                away_score=away_score,
                season=season,
                is_playoff=True
            )

            # Update rivalry intensity and create playoff rivalries (Milestone 11, Tollgate 6)
            from ..services.rivalry_service import RivalryService, PlayoffRound

            # Map round name to PlayoffRound enum
            playoff_round_map = {
                "wild_card": PlayoffRound.WILD_CARD,
                "divisional": PlayoffRound.DIVISIONAL,
                "conference": PlayoffRound.CONFERENCE,
                "super_bowl": PlayoffRound.SUPER_BOWL,
            }
            playoff_round = playoff_round_map.get(round_name.lower())

            if playoff_round:
                rivalry_service = RivalryService(gc_db)

                # First, try to create a new rivalry if none exists
                rivalry_service.create_playoff_rivalry(
                    dynasty_id=dynasty_id,
                    team_a_id=home_team_id,
                    team_b_id=away_team_id,
                    playoff_round=playoff_round,
                    season=season,
                )

                # Then update the rivalry intensity
                rivalry_service.update_rivalry_after_game(
                    dynasty_id=dynasty_id,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_score=home_score,
                    away_score=away_score,
                    overtime_periods=sim_result.overtime_periods,
                    is_playoff=True,
                    playoff_round=playoff_round,
                )

        result = {
            "game_id": game_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "round": round_name,
            "injuries": game_injuries,
            "drives": sim_result.drives,  # Play-by-play data (FULL mode)
            "game_result": sim_result,  # Full result for UI access (key must match StageView expectation)
        }

        # Log the game result for visibility
        self._log_game_result(result, round_name)

        return result

    def _persist_box_scores(
        self,
        context: Dict[str, Any],
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        player_stats: List[Dict[str, Any]],
        home_team_stats: Dict[str, Any] = None,
        away_team_stats: Dict[str, Any] = None
    ) -> None:
        """
        Persist box scores for a game using team stats with player stats fallback.

        Team stats (from simulation) include first_downs, 3rd/4th down, TOP,
        penalties - data that cannot be derived from player stats alone.

        Args:
            context: Execution context with unified_api
            game_id: Game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            player_stats: List of player stat dicts from simulation
            home_team_stats: Optional team-level stats dict from simulation
            away_team_stats: Optional team-level stats dict from simulation
        """
        if not player_stats:
            return

        try:
            from ..database.box_scores_api import BoxScoresAPI
            unified_api = context["unified_api"]

            # Start with player stats aggregation
            home_box = BoxScoresAPI.aggregate_from_player_stats(player_stats, home_team_id)
            away_box = BoxScoresAPI.aggregate_from_player_stats(player_stats, away_team_id)

            # Override with team stats if available (maps field names correctly)
            if home_team_stats:
                home_box['first_downs'] = home_team_stats.get('first_downs', 0)
                home_box['third_down_att'] = home_team_stats.get('third_down_attempts', 0)
                home_box['third_down_conv'] = home_team_stats.get('third_down_conversions', 0)
                home_box['fourth_down_att'] = home_team_stats.get('fourth_down_attempts', 0)
                home_box['fourth_down_conv'] = home_team_stats.get('fourth_down_conversions', 0)
                home_box['time_of_possession'] = int(home_team_stats.get('time_of_possession_seconds', 0))
                home_box['penalties'] = home_team_stats.get('penalties', 0)
                home_box['penalty_yards'] = home_team_stats.get('penalty_yards', 0)

            if away_team_stats:
                away_box['first_downs'] = away_team_stats.get('first_downs', 0)
                away_box['third_down_att'] = away_team_stats.get('third_down_attempts', 0)
                away_box['third_down_conv'] = away_team_stats.get('third_down_conversions', 0)
                away_box['fourth_down_att'] = away_team_stats.get('fourth_down_attempts', 0)
                away_box['fourth_down_conv'] = away_team_stats.get('fourth_down_conversions', 0)
                away_box['time_of_possession'] = int(away_team_stats.get('time_of_possession_seconds', 0))
                away_box['penalties'] = away_team_stats.get('penalties', 0)
                away_box['penalty_yards'] = away_team_stats.get('penalty_yards', 0)

            unified_api.box_scores_insert(
                game_id=game_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_box=home_box,
                away_box=away_box
            )
            print(f"[PlayoffHandler] Inserted box scores for game {game_id}")
        except Exception as e:
            print(f"[WARNING PlayoffHandler] Failed to persist box scores for {game_id}: {e}")

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

    def _generate_playoff_headline(
        self,
        context: Dict[str, Any],
        game_result: Dict[str, Any],
        round_name: str,
        sim_result: Any = None
    ) -> None:
        """
        Generate and persist headline for a completed playoff game.

        Args:
            context: Execution context with dynasty_id, season, db_path
            game_result: Game result dict with scores and team IDs
            round_name: Playoff round name (wild_card, divisional, etc.)
            sim_result: Optional simulation result with drives/injuries
        """
        try:
            from game_cycle.services.headline_generator import HeadlineGenerator
            from game_cycle.database.media_coverage_api import MediaCoverageAPI
            from game_cycle.database.connection import GameCycleDatabase

            dynasty_id = context["dynasty_id"]
            season = context["season"]
            db_path = context.get("db_path") or context["unified_api"].database_path

            home_team_id = game_result["home_team_id"]
            away_team_id = game_result["away_team_id"]
            home_score = game_result["home_score"]
            away_score = game_result["away_score"]
            game_id = game_result.get("game_id", "")

            # Determine winner/loser
            if home_score > away_score:
                winner_id, loser_id = home_team_id, away_team_id
                winner_score, loser_score = home_score, away_score
            else:
                winner_id, loser_id = away_team_id, home_team_id
                winner_score, loser_score = away_score, home_score

            # Calculate week for this playoff round
            week = self._round_to_week(round_name)

            # Build game data for headline generation
            game_data = {
                "game_id": game_id,
                "week": week,
                "winner_id": winner_id,
                "loser_id": loser_id,
                "winner_score": winner_score,
                "loser_score": loser_score,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "is_playoff": True,
                "playoff_round": round_name,
                "overtime_periods": getattr(sim_result, 'overtime_periods', 0) if sim_result else 0,
            }

            # Generate headline
            generator = HeadlineGenerator(db_path, dynasty_id, season)
            headline = generator.generate_game_headline(game_data, include_body_text=True)

            if not headline:
                print(f"[PlayoffHandler] No headline generated for {game_id}")
                return

            # Persist to database
            gc_db = GameCycleDatabase(db_path)
            try:
                media_api = MediaCoverageAPI(gc_db)
                media_api.save_headline(
                    dynasty_id=dynasty_id,
                    season=season,
                    week=week,
                    headline_data={
                        'headline_type': headline.headline_type,
                        'headline': headline.headline,
                        'subheadline': headline.subheadline,
                        'body_text': headline.body_text,
                        'sentiment': headline.sentiment,
                        'priority': headline.priority + 20,  # Boost priority for playoff games
                        'team_ids': [home_team_id, away_team_id],
                        'player_ids': headline.player_ids or [],
                        'game_id': game_id,
                        'metadata': {'playoff_round': round_name}
                    }
                )
                print(f"[PlayoffHandler] Generated headline for playoff game: {headline.headline[:50]}...")
            finally:
                gc_db.close()

        except Exception as e:
            # Log but don't fail game simulation for headline errors
            print(f"[PlayoffHandler] Failed to generate headline for playoff game: {e}")

    def _generate_playoff_social_posts(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        week: int,
        round_name: str,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        sim_result
    ) -> int:
        """
        Generate and persist social media posts for a playoff game.

        Similar to regular season posts, but with playoff context.
        Posts will mention the playoff round and have higher engagement.

        Args:
            db_path: Database path
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            round_name: Playoff round name (wild_card, divisional, conference, super_bowl)
            game_id: Game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_score: Home team final score
            away_score: Away team final score
            sim_result: SimulationResult with game details

        Returns:
            Number of posts generated (0 on failure)
        """
        try:
            from ..services.social_generators.factory import SocialPostGeneratorFactory
            from ..models.social_event_types import SocialEventType
            from ..database.connection import GameCycleDatabase

            print(f"[SOCIAL] Generating playoff posts for {game_id} ({round_name})")

            # Determine winner/loser
            if home_score > away_score:
                winner_id, loser_id = home_team_id, away_team_id
                winner_score, loser_score = home_score, away_score
            else:
                winner_id, loser_id = away_team_id, home_team_id
                winner_score, loser_score = away_score, home_score

            # Calculate game characteristics
            score_margin = abs(home_score - away_score)
            is_blowout = score_margin >= 21
            # Playoff upsets: Lower seed beating higher seed
            is_upset = False  # TODO: Implement playoff seeding upset detection

            # Extract star players from sim result
            star_players = {}
            if hasattr(sim_result, 'player_stats') and sim_result.player_stats:
                for team_id in [home_team_id, away_team_id]:
                    team_stats = [p for p in sim_result.player_stats if p.get('team_id') == team_id]
                    if team_stats:
                        def get_total_yards(p):
                            return (
                                (p.get('passing_yards') or 0) +
                                (p.get('rushing_yards') or 0) +
                                (p.get('receiving_yards') or 0)
                            )
                        top_player = max(team_stats, key=get_total_yards, default=None)
                        if top_player:
                            star_players[team_id] = top_player.get('player_name', 'Unknown')

            # Build event data for generator
            event_data = {
                'winning_team_id': winner_id,
                'losing_team_id': loser_id,
                'winning_score': winner_score,
                'losing_score': loser_score,
                'game_id': game_id,
                'is_upset': is_upset,
                'is_blowout': is_blowout,
                'star_players': star_players if star_players else None,
                'season_type': 'playoffs',  # KEY: Mark as playoff game
                'round_name': round_name    # KEY: Include playoff round
            }

            # Generate and persist posts using factory (NEW ARCHITECTURE)
            gc_db = GameCycleDatabase(db_path)
            try:
                posts_created = SocialPostGeneratorFactory.generate_posts(
                    event_type=SocialEventType.GAME_RESULT,
                    db=gc_db,
                    dynasty_id=dynasty_id,
                    season=season,
                    week=week,
                    event_data=event_data
                )

                print(f"[SOCIAL] ✓ Generated {posts_created} playoff posts for {round_name} game {game_id}")
                return posts_created
            finally:
                gc_db.commit()  # CRITICAL: Flush WAL to main DB before closing
                gc_db.close()

        except Exception as e:
            print(f"[PlayoffHandler] Error generating social posts for {game_id}: {e}")
            import traceback
            traceback.print_exc()
            return 0

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

        Uses playoff_bracket table to show matchups BEFORE and AFTER games.
        This ensures games panel shows seeded matchups even before simulation.

        Args:
            stage: The playoff stage
            context: Execution context

        Returns:
            Preview with matchups, seeds, home field, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        round_name = self.ROUND_NAMES.get(stage.stage_type, "unknown")

        # Use playoff_bracket table (has seeded matchups before games played)
        bracket_matchups = self._get_bracket_matchups(round_name, context)

        # Get standings for team record info
        standings_data = unified_api.standings_get(season)

        # Build standings lookup from 'overall' list
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
        for m in bracket_matchups:
            # higher_seed = home team (has home field advantage)
            home_team_id = m.get("higher_seed")
            away_team_id = m.get("lower_seed")

            # Generate consistent game_id for box score lookup
            game_id = f"playoff_{season}_{round_name}_{home_team_id}_{away_team_id}"

            # Get standings (EnhancedTeamStanding objects or None)
            home_standing = standings_lookup.get(home_team_id)
            away_standing = standings_lookup.get(away_team_id)

            # Get team info from team loader
            home_team = team_loader.get_team_by_id(home_team_id)
            away_team = team_loader.get_team_by_id(away_team_id)

            matchups.append({
                "game_id": game_id,
                "home_team": {
                    "team_id": home_team_id,
                    "name": home_team.full_name if home_team else f"Team {home_team_id}",
                    "abbreviation": home_team.abbreviation if home_team else "???",
                    "record": f"{home_standing.wins if home_standing else 0}-{home_standing.losses if home_standing else 0}",
                },
                "away_team": {
                    "team_id": away_team_id,
                    "name": away_team.full_name if away_team else f"Team {away_team_id}",
                    "abbreviation": away_team.abbreviation if away_team else "???",
                    "record": f"{away_standing.wins if away_standing else 0}-{away_standing.losses if away_standing else 0}",
                },
                "is_played": m.get("winner") is not None,
                "home_score": m.get("home_score"),
                "away_score": m.get("away_score"),
            })

        return {
            "round": round_name,
            "display_name": self._get_round_display_name(stage.stage_type),
            "matchups": matchups,
            "game_count": len(bracket_matchups),
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

    # =========================================================================
    # Playoff Bracket Table Methods (for pre-seeding matchups before simulation)
    # =========================================================================

    def seed_bracket(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seed the playoff bracket for a round (create matchups WITHOUT simulating).

        This is called when entering a playoff stage, BEFORE execute().
        Creates matchups in playoff_bracket table with NULL scores/winner.

        Args:
            stage: The playoff stage to seed
            context: Execution context with dynasty_id, season, db_path

        Returns:
            Dict with matchups created
        """
        round_name = self.ROUND_NAMES.get(stage.stage_type, "unknown")

        # Check if matchups already exist for this round
        existing = self._get_bracket_matchups(round_name, context)
        if existing:
            return {"matchups": existing, "already_seeded": True}

        # Seed based on round
        if round_name == "wild_card":
            matchups = self._seed_wild_card_bracket(context)
        elif round_name == "divisional":
            matchups = self._seed_divisional_bracket(context)
        elif round_name == "conference":
            matchups = self._seed_conference_bracket(context)
        elif round_name == "super_bowl":
            matchups = self._seed_super_bowl_bracket(context)
        else:
            matchups = []

        return {"matchups": matchups, "already_seeded": False}

    def _seed_wild_card_bracket(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed Wild Card matchups into playoff_bracket table.

        Creates 6 matchups: 3 per conference (#2 vs #7, #3 vs #6, #4 vs #5)
        """
        unified_api = context["unified_api"]
        season = context["season"]

        from playoff_system.playoff_seeder import PlayoffSeeder
        seeder = PlayoffSeeder()

        standings_data = unified_api.standings_get(season)
        standings_dict = self._build_standings_dict(standings_data)
        seeding = seeder.calculate_seeding(standings_dict, season=season, week=18)

        matchups = []
        game_number = 1
        all_playoff_teams = []

        for conference in ["AFC", "NFC"]:
            seeds = self._get_seeds_for_conference(seeding, conference)

            if len(seeds) >= 7:
                # Track all playoff teams (seeds 1-7 for each conference)
                all_playoff_teams.extend(seeds[:7])

                # #2 vs #7
                matchup = self._insert_bracket_matchup(
                    context, "wild_card", conference, game_number,
                    higher_seed=seeds[1], lower_seed=seeds[6],
                    higher_seed_num=2, lower_seed_num=7
                )
                matchups.append(matchup)
                game_number += 1

                # #3 vs #6
                matchup = self._insert_bracket_matchup(
                    context, "wild_card", conference, game_number,
                    higher_seed=seeds[2], lower_seed=seeds[5],
                    higher_seed_num=3, lower_seed_num=6
                )
                matchups.append(matchup)
                game_number += 1

                # #4 vs #5
                matchup = self._insert_bracket_matchup(
                    context, "wild_card", conference, game_number,
                    higher_seed=seeds[3], lower_seed=seeds[4],
                    higher_seed_num=4, lower_seed_num=5
                )
                matchups.append(matchup)
                game_number += 1

        # Mark all playoff teams in standings
        if all_playoff_teams:
            self._mark_teams_made_playoffs(context, all_playoff_teams)

        return matchups

    def _seed_divisional_bracket(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed Divisional matchups based on Wild Card winners.

        #1 seed plays lowest remaining seed.
        Other two winners play each other (higher seed hosts).
        """
        matchups = []
        game_number = 1

        for conference in ["AFC", "NFC"]:
            seeds = self._get_conference_seeds(conference, context)
            wild_card_winners = self._get_bracket_round_winners("wild_card", conference, context)

            if not wild_card_winners or len(seeds) < 1:
                continue

            seed_1 = seeds[0]

            # Map winners to their seed numbers
            winner_seeds = []
            for winner_id in wild_card_winners:
                for i, seed_id in enumerate(seeds):
                    if seed_id == winner_id:
                        winner_seeds.append((i + 1, winner_id))
                        break

            winner_seeds.sort()

            if len(winner_seeds) >= 3:
                # #1 plays lowest remaining (highest seed number)
                lowest_remaining = winner_seeds[-1]
                matchup = self._insert_bracket_matchup(
                    context, "divisional", conference, game_number,
                    higher_seed=seed_1, lower_seed=lowest_remaining[1],
                    higher_seed_num=1, lower_seed_num=lowest_remaining[0]
                )
                matchups.append(matchup)
                game_number += 1

                # Two highest remaining play each other
                higher = winner_seeds[0]
                lower = winner_seeds[1]
                matchup = self._insert_bracket_matchup(
                    context, "divisional", conference, game_number,
                    higher_seed=higher[1], lower_seed=lower[1],
                    higher_seed_num=higher[0], lower_seed_num=lower[0]
                )
                matchups.append(matchup)
                game_number += 1

        return matchups

    def _seed_conference_bracket(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed Conference Championship matchups based on Divisional winners.
        """
        matchups = []
        game_number = 1

        for conference in ["AFC", "NFC"]:
            divisional_winners = self._get_bracket_round_winners("divisional", conference, context)

            if len(divisional_winners) == 2:
                seeds = self._get_conference_seeds(conference, context)
                seed_map = {team_id: i + 1 for i, team_id in enumerate(seeds)}

                team1, team2 = divisional_winners
                seed1 = seed_map.get(team1, 99)
                seed2 = seed_map.get(team2, 99)

                if seed1 < seed2:
                    higher, lower = team1, team2
                    higher_num, lower_num = seed1, seed2
                else:
                    higher, lower = team2, team1
                    higher_num, lower_num = seed2, seed1

                matchup = self._insert_bracket_matchup(
                    context, "conference", conference, game_number,
                    higher_seed=higher, lower_seed=lower,
                    higher_seed_num=higher_num, lower_seed_num=lower_num
                )
                matchups.append(matchup)
                game_number += 1

        return matchups

    def _seed_super_bowl_bracket(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Seed Super Bowl matchup based on Conference Championship winners.
        """
        afc_winners = self._get_bracket_round_winners("conference", "AFC", context)
        nfc_winners = self._get_bracket_round_winners("conference", "NFC", context)

        if not afc_winners or not nfc_winners:
            return []

        # For Super Bowl, use SUPER_BOWL as conference (per schema constraint)
        matchup = self._insert_bracket_matchup(
            context, "super_bowl", "SUPER_BOWL", 1,
            higher_seed=afc_winners[0], lower_seed=nfc_winners[0],
            higher_seed_num=None, lower_seed_num=None  # Seeds don't apply to Super Bowl
        )
        return [matchup]

    def _insert_bracket_matchup(
        self,
        context: Dict[str, Any],
        round_name: str,
        conference: str,
        game_number: int,
        higher_seed: int,
        lower_seed: int,
        higher_seed_num: int = None,
        lower_seed_num: int = None
    ) -> Dict[str, Any]:
        """
        Insert a matchup into the playoff_bracket table.

        Args:
            context: Execution context with dynasty_id, season, db_path
            round_name: 'wild_card', 'divisional', 'conference', 'super_bowl'
            conference: 'AFC', 'NFC', or 'SUPER_BOWL'
            game_number: Game number within round/conference
            higher_seed: Team ID of higher seed (home team)
            lower_seed: Team ID of lower seed (away team)
            higher_seed_num: Seed number of higher seed (for display)
            lower_seed_num: Seed number of lower seed (for display)

        Returns:
            Dict with matchup info
        """
        from ..database.connection import GameCycleDatabase
        from ..database.playoff_bracket_api import PlayoffBracketAPI

        dynasty_id = context["dynasty_id"]
        season = context["season"]

        db = GameCycleDatabase()  # Uses default game_cycle.db
        api = PlayoffBracketAPI(db)

        matchup = api.insert_matchup(
            dynasty_id=dynasty_id,
            season=season,
            round_name=round_name,
            conference=conference,
            game_number=game_number,
            higher_seed=higher_seed,
            lower_seed=lower_seed
        )

        # Return dict for backward compatibility
        result = matchup.to_dict()
        result["higher_seed_num"] = higher_seed_num
        result["lower_seed_num"] = lower_seed_num
        return result

    def _get_bracket_matchups(
        self,
        round_name: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get matchups from playoff_bracket table for a round.

        Args:
            round_name: 'wild_card', 'divisional', 'conference', 'super_bowl'
            context: Execution context with dynasty_id, season, db_path

        Returns:
            List of matchup dicts
        """
        from ..database.connection import GameCycleDatabase
        from ..database.playoff_bracket_api import PlayoffBracketAPI

        dynasty_id = context["dynasty_id"]
        season = context["season"]

        db = GameCycleDatabase()  # Uses default game_cycle.db
        api = PlayoffBracketAPI(db)

        matchups = api.get_matchups_for_round(dynasty_id, season, round_name)
        return [m.to_dict() for m in matchups]

    def _get_bracket_round_winners(
        self,
        round_name: str,
        conference: str,
        context: Dict[str, Any]
    ) -> List[int]:
        """
        Get winners from playoff_bracket for a specific round and conference.

        Args:
            round_name: Playoff round name
            conference: 'AFC' or 'NFC'
            context: Execution context with dynasty_id, season, db_path

        Returns:
            List of winning team IDs
        """
        from ..database.connection import GameCycleDatabase
        from ..database.playoff_bracket_api import PlayoffBracketAPI

        dynasty_id = context["dynasty_id"]
        season = context["season"]

        db = GameCycleDatabase()  # Uses default game_cycle.db
        api = PlayoffBracketAPI(db)

        winners = api.get_round_winners(dynasty_id, season, round_name, conference)
        return winners

    def _update_bracket_result(
        self,
        context: Dict[str, Any],
        round_name: str,
        conference: str,
        game_number: int,
        home_score: int,
        away_score: int,
        winner: int
    ) -> None:
        """
        Update playoff_bracket with game result.

        Args:
            context: Execution context with dynasty_id, season, db_path
            round_name: Playoff round
            conference: Conference
            game_number: Game number
            home_score: Home team score
            away_score: Away team score
            winner: Winning team ID
        """
        from ..database.connection import GameCycleDatabase
        from ..database.playoff_bracket_api import PlayoffBracketAPI

        dynasty_id = context["dynasty_id"]
        season = context["season"]

        db = GameCycleDatabase()  # Uses default game_cycle.db
        api = PlayoffBracketAPI(db)

        api.update_result(
            dynasty_id=dynasty_id,
            season=season,
            round_name=round_name,
            conference=conference,
            game_number=game_number,
            home_score=home_score,
            away_score=away_score,
            winner=winner
        )

    # =========================================================================
    # Injury Generation Methods (Simplified for Playoffs)
    # =========================================================================

    def _generate_playoff_injuries(
        self,
        context: Dict[str, Any],
        home_team_id: int,
        away_team_id: int,
        game_id: str,
        round_name: str
    ) -> List[Dict[str, Any]]:
        """
        Generate injuries for a playoff game using simplified logic.

        Since playoffs don't use MockStatsGenerator (no snap count data),
        we assume ~50% of each roster played and roll injury checks.

        Args:
            context: Execution context with dynasty_id, season, db_path
            home_team_id: Home team ID
            away_team_id: Away team ID
            game_id: Game identifier
            round_name: Playoff round name

        Returns:
            List of injury dicts for recording
        """
        from ..services.injury_service import InjuryService

        dynasty_id = context["dynasty_id"]
        season = context["season"]
        db_path = context.get("db_path")

        if not db_path:
            unified_api = context.get("unified_api")
            if unified_api:
                db_path = unified_api.database_path

        if not db_path:
            return []

        injury_service = InjuryService(db_path, dynasty_id, season)
        week = self._round_to_week(round_name)

        injuries = []

        for team_id in [home_team_id, away_team_id]:
            roster = self._get_active_roster(team_id, context)

            for player in roster:
                # Simplified: assume 50% chance player participated
                if random.random() < 0.5:
                    injury = injury_service.generate_injury(
                        player=player,
                        week=week,
                        occurred_during='game',
                        game_id=game_id
                    )

                    if injury:
                        injury_service.record_injury(injury)
                        injuries.append({
                            'player_id': injury.player_id,
                            'player_name': injury.player_name,
                            'team_id': injury.team_id,
                            'injury_type': injury.injury_type.value,
                            'weeks_out': injury.weeks_out,
                            'severity': injury.severity.value
                        })

        if injuries:
            print(f"[DEBUG PlayoffHandler] Recorded {len(injuries)} injuries for game {game_id}")

        return injuries

    def _get_active_roster(
        self,
        team_id: int,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get active roster for a team.

        Args:
            team_id: Team ID
            context: Execution context with db_path, dynasty_id

        Returns:
            List of player dicts with needed fields for injury generation
        """
        dynasty_id = context["dynasty_id"]
        db_path = context.get("db_path")

        if not db_path:
            unified_api = context.get("unified_api")
            if unified_api:
                db_path = unified_api.database_path

        if not db_path:
            return []

        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT
                        p.player_id,
                        p.first_name,
                        p.last_name,
                        p.team_id,
                        p.positions,
                        p.attributes,
                        p.birthdate
                    FROM players p
                    JOIN team_rosters tr ON p.dynasty_id = tr.dynasty_id
                                        AND p.player_id = tr.player_id
                    WHERE p.dynasty_id = ?
                      AND p.team_id = ?
                      AND tr.roster_status = 'active'
                """, (dynasty_id, team_id))

                players = []
                for row in cursor.fetchall():
                    positions = json.loads(row['positions']) if row['positions'] else []
                    attributes = json.loads(row['attributes']) if row['attributes'] else {}

                    players.append({
                        'player_id': row['player_id'],
                        'first_name': row['first_name'],
                        'last_name': row['last_name'],
                        'team_id': row['team_id'],
                        'positions': positions,
                        'attributes': attributes,
                        'birthdate': row['birthdate']
                    })

                return players
        except Exception as e:
            print(f"[WARNING PlayoffHandler] Failed to get roster for team {team_id}: {e}")
            return []

    def _update_standings_playoff_flags(
        self,
        context: Dict[str, Any],
        round_name: str,
        games_played: List[Dict[str, Any]]
    ) -> None:
        """
        Update standings table with playoff achievement flags.

        After each playoff round, updates the standings to reflect which teams:
        - made_playoffs: All 14 playoff teams (set during Wild Card seeding)
        - won_wild_card: Teams that won Wild Card round
        - won_division_round: Teams that won Divisional round
        - won_conference: Teams that won Conference Championship
        - won_super_bowl: Super Bowl winner

        Args:
            context: Execution context with dynasty_id, season, unified_api
            round_name: The playoff round that was just completed
            games_played: List of game results with winner information
        """
        unified_api = context["unified_api"]
        dynasty_id = context["dynasty_id"]
        season = context["season"]
        db_path = context.get("db_path") or unified_api.database_path

        # Map round names to standing column names
        round_to_column = {
            "wild_card": "won_wild_card",
            "divisional": "won_division_round",
            "conference": "won_conference",
            "super_bowl": "won_super_bowl",
        }

        column = round_to_column.get(round_name)
        if not column:
            return

        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Collect all winning team IDs from this round
                winners = []
                for game in games_played:
                    # Determine winner from scores
                    home_score = game.get("home_score", 0)
                    away_score = game.get("away_score", 0)
                    home_team = game.get("home_team_id")
                    away_team = game.get("away_team_id")

                    if home_score > away_score:
                        winners.append(home_team)
                    elif away_score > home_score:
                        winners.append(away_team)
                    # Ties shouldn't happen in playoffs, but handle gracefully

                # Update standings for each winner
                for team_id in winners:
                    cursor.execute(f"""
                        UPDATE standings
                        SET {column} = 1
                        WHERE dynasty_id = ? AND team_id = ? AND season = ?
                    """, (dynasty_id, team_id, season))

                conn.commit()
                print(f"[PlayoffHandler] Updated {column} for {len(winners)} teams: {winners}")

        except Exception as e:
            print(f"[WARNING PlayoffHandler] Failed to update standings playoff flags: {e}")

    def _mark_teams_made_playoffs(
        self,
        context: Dict[str, Any],
        playoff_teams: List[int]
    ) -> None:
        """
        Mark teams as having made the playoffs in standings.

        Called during Wild Card seeding to set made_playoffs=1 for all 14 teams.

        Args:
            context: Execution context with dynasty_id, season, unified_api
            playoff_teams: List of team IDs that made playoffs
        """
        unified_api = context["unified_api"]
        dynasty_id = context["dynasty_id"]
        season = context["season"]
        db_path = context.get("db_path") or unified_api.database_path

        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                for team_id in playoff_teams:
                    cursor.execute("""
                        UPDATE standings
                        SET made_playoffs = 1
                        WHERE dynasty_id = ? AND team_id = ? AND season = ?
                    """, (dynasty_id, team_id, season))

                conn.commit()
                print(f"[PlayoffHandler] Marked {len(playoff_teams)} teams as made_playoffs")

        except Exception as e:
            print(f"[WARNING PlayoffHandler] Failed to mark teams made_playoffs: {e}")