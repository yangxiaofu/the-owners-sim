"""
Game Result Processor

Specialized processor for NFL game results that handles standings updates,
player statistics, injuries, team momentum, and playoff implications.
"""

from typing import Dict, Any, List, Optional
from ..results.base_result import AnySimulationResult, ProcessingContext, ProcessingResult
from ..results.game_result import GameResult
from .base_processor import BaseResultProcessor, ProcessingStrategy


class GameResultProcessor(BaseResultProcessor):
    """
    Processes NFL game results with comprehensive season progression updates.
    
    Handles:
    - Win/loss standings updates
    - Player statistics aggregation
    - Injury processing and roster impacts
    - Team momentum and morale changes
    - Playoff implications and divisional standings
    - Historical game records
    """
    
    def can_process(self, result: AnySimulationResult) -> bool:
        """Check if this is a GameResult or SimulationResult with game data"""
        # Direct GameResult
        if isinstance(result, GameResult):
            return True
        
        # SimulationResult from GameSimulationEvent
        from ..events.base_simulation_event import SimulationResult
        if isinstance(result, SimulationResult):
            # Check if it has game metadata
            metadata = getattr(result, 'metadata', {})
            return (metadata.get('game_type') == 'nfl_game' and 
                   'game_result_object' in metadata)
        
        return False
    
    def process_result(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """Process game result with comprehensive season impact"""

        self.logger.info(f"🔍 GameResultProcessor.process_result called with {type(result).__name__}")

        # Extract GameResult from either direct GameResult or SimulationResult
        game_result = self._extract_game_result(result)
        if game_result is None:
            self.logger.warning(f"⚠️ Could not extract GameResult from {type(result).__name__}")
            return ProcessingResult(
                processed_successfully=False,
                processing_type="GameResultProcessor",
                error_messages=["Could not extract GameResult from simulation result"]
            )

        self.logger.info(f"🔍 Extracted GameResult with {len(game_result.player_stats)} player stats")

        processing_result = ProcessingResult(
            processed_successfully=True,
            processing_type="GameResultProcessor"
        )

        # Process based on configured strategy
        self.logger.info(f"🔍 Processing with strategy: {self.config.strategy}")
        if self.config.strategy == ProcessingStrategy.STATISTICS_ONLY:
            self._process_statistics_only(game_result, context, processing_result)
        else:
            self._process_full_game_impact(game_result, context, processing_result)

        return processing_result
    
    def _extract_game_result(self, result: AnySimulationResult) -> Optional[GameResult]:
        """Extract GameResult from either GameResult or SimulationResult"""
        # Direct GameResult
        if isinstance(result, GameResult):
            return result
        
        # SimulationResult from GameSimulationEvent
        from ..events.base_simulation_event import SimulationResult
        if isinstance(result, SimulationResult):
            metadata = getattr(result, 'metadata', {})
            game_result_obj = metadata.get('game_result_object')
            
            if game_result_obj:
                # Convert FullGameSimulator result to GameResult format
                # The game_result_obj is from GameLoopController.GameResult
                try:
                    # Extract team IDs from Team objects
                    away_team_id = metadata.get('away_team_id', 0)
                    home_team_id = metadata.get('home_team_id', 0)
                    
                    # Extract scores from final_score dict with team ID keys
                    final_score = metadata.get('final_score', {})
                    if isinstance(final_score, dict):
                        # Use the new team ID-keyed scores structure
                        scores_dict = final_score.get('scores', {})
                        if scores_dict:
                            # Direct team ID lookup from FullGameSimulator structure
                            away_score = scores_dict.get(away_team_id, 0)
                            home_score = scores_dict.get(home_team_id, 0)
                        else:
                            # Fallback for direct team ID lookup (backwards compatibility)
                            away_score = final_score.get(away_team_id, 0)
                            home_score = final_score.get(home_team_id, 0)
                    else:
                        # Fallback to parsing final_score if it's a string like "18-6"
                        try:
                            scores = str(final_score).split('-')
                            away_score = int(scores[0]) if len(scores) > 0 else 0
                            home_score = int(scores[1]) if len(scores) > 1 else 0
                        except:
                            away_score = 0
                            home_score = 0
                    
                    # Extract player statistics from the game result object
                    player_stats = []

                    # Try different methods to extract player statistics
                    if hasattr(game_result_obj, 'player_stats') and game_result_obj.player_stats:
                        # Direct player_stats attribute
                        player_stats = game_result_obj.player_stats
                    elif hasattr(game_result_obj, 'get_player_stats'):
                        # FullGameSimulator method
                        try:
                            stats_data = game_result_obj.get_player_stats()
                            player_stats = self._convert_simulator_player_stats(stats_data, home_team_id, away_team_id)
                        except Exception as e:
                            self.logger.warning(f"Failed to extract player stats via get_player_stats(): {e}")
                    elif hasattr(game_result_obj, 'final_statistics') and game_result_obj.final_statistics:
                        # Check in final_statistics
                        final_stats = game_result_obj.final_statistics
                        if 'player_statistics' in final_stats:
                            stats_data = final_stats['player_statistics']
                            player_stats = self._convert_simulator_player_stats(stats_data, home_team_id, away_team_id)

                    # Ensure player_stats is a list (not None)
                    if player_stats is None:
                        player_stats = []

                    self.logger.info(f"🔍 Extracting {len(player_stats)} player stats from game result object")

                    game_result = GameResult(
                        event_type=result.event_type,
                        event_name=result.event_name,
                        date=result.date,
                        teams_affected=result.teams_affected,
                        duration_hours=result.duration_hours,
                        success=result.success,
                        away_team_id=away_team_id,
                        home_team_id=home_team_id,
                        away_score=away_score,
                        home_score=home_score,
                        week=metadata.get('week', 1),
                        season_type=metadata.get('season_type', 'regular_season'),
                        total_plays=getattr(game_result_obj, 'total_plays', 0),
                        total_drives=getattr(game_result_obj, 'total_drives', 0),
                        game_duration_minutes=getattr(game_result_obj, 'game_duration_minutes', 60),
                        player_stats=player_stats  # Add player statistics to the GameResult
                    )
                    return game_result
                except Exception as e:
                    self.logger.error(f"Failed to convert game result: {e}")
                    return None
        
        return None

    def _convert_simulator_player_stats(self, stats_data: Any, home_team_id: int = None, away_team_id: int = None) -> List[Any]:
        """Convert FullGameSimulator player statistics to GameResult format."""
        try:
            player_stats = []

            # Handle different formats from FullGameSimulator
            if isinstance(stats_data, dict):
                # Check for 'all_players' list format
                if 'all_players' in stats_data and isinstance(stats_data['all_players'], list):
                    for player_data in stats_data['all_players']:
                        if isinstance(player_data, dict):
                            # Convert to our expected player stat format
                            # Pass team context for proper team assignment
                            player_stat = self._create_player_stat_from_data(player_data, home_team_id, away_team_id)
                            if player_stat:
                                player_stats.append(player_stat)

            self.logger.info(f"🔍 Converted {len(player_stats)} player stats from simulator format")
            return player_stats

        except Exception as e:
            self.logger.error(f"Failed to convert simulator player stats: {e}")
            return []

    def _create_player_stat_from_data(self, player_data: Dict[str, Any], home_team_id: int = None, away_team_id: int = None) -> Optional[Any]:
        """Create a player stat object from simulator data."""
        try:
            # Extract basic player info
            player_name = player_data.get('name', 'Unknown Player')
            team_id = player_data.get('team_id', None)
            position = player_data.get('position', 'UNK')

            # Fix: Infer team_id from player name if not provided
            if team_id is None or team_id == 0:
                print(f"🔍 DEBUG: Inferring team for {player_name} (was: {team_id})")
                team_id = self._infer_team_from_player_name(player_name, home_team_id, away_team_id)
                print(f"🔍 DEBUG: Assigned {player_name} to Team {team_id}")

            # Extract statistics with defaults
            passing_yards = player_data.get('passing_yards', 0)
            passing_tds = player_data.get('passing_touchdowns', 0)
            rushing_yards = player_data.get('rushing_yards', 0)
            rushing_tds = player_data.get('rushing_touchdowns', 0)
            receiving_yards = player_data.get('receiving_yards', 0)
            receiving_tds = player_data.get('receiving_touchdowns', 0)

            # Create a simple player stat object (you may need to adjust this based on your actual PlayerStat class)
            from dataclasses import dataclass

            @dataclass
            class SimplePlayerStat:
                player_name: str
                team_id: int
                position: str
                passing_yards: int = 0
                passing_tds: int = 0
                rushing_yards: int = 0
                rushing_tds: int = 0
                receiving_yards: int = 0
                receiving_tds: int = 0

                def get_total_yards(self):
                    return self.passing_yards + self.rushing_yards + self.receiving_yards

                def get_total_touchdowns(self):
                    return self.passing_tds + self.rushing_tds + self.receiving_tds

            return SimplePlayerStat(
                player_name=player_name,
                team_id=team_id,
                position=position,
                passing_yards=passing_yards,
                passing_tds=passing_tds,
                rushing_yards=rushing_yards,
                rushing_tds=rushing_tds,
                receiving_yards=receiving_yards,
                receiving_tds=receiving_tds
            )

        except Exception as e:
            self.logger.error(f"Failed to create player stat from data: {e}")
            return None

    def _infer_team_from_player_name(self, player_name: str, home_team_id: int, away_team_id: int) -> int:
        """
        Infer team_id from player name using the players.json database.

        Real NFL players have team_id mapped in players.json. For generated names,
        fall back to team name matching.
        """
        if not player_name or not home_team_id or not away_team_id:
            return home_team_id or 0  # Default to home team if can't determine

        try:
            # First, try to look up the player in the players.json database
            team_id = self._lookup_player_team_from_database(player_name, home_team_id, away_team_id)
            if team_id:
                return team_id

            # Fallback: check for team city names in player name (for generated players)
            from constants.team_ids import get_team_by_id

            home_team = get_team_by_id(home_team_id)
            away_team = get_team_by_id(away_team_id)

            if home_team and away_team:
                home_city = home_team.city.lower()
                away_city = away_team.city.lower()
                player_name_lower = player_name.lower()

                # Check if player name contains team city
                if home_city in player_name_lower:
                    return home_team_id
                elif away_city in player_name_lower:
                    return away_team_id

            # If can't determine from name, alternate assignment to ensure both teams represented
            player_hash = hash(player_name) % 2
            return away_team_id if player_hash == 0 else home_team_id

        except Exception as e:
            self.logger.warning(f"Failed to infer team from player name '{player_name}': {e}")
            return home_team_id  # Default to home team

    def _lookup_player_team_from_database(self, player_name: str, home_team_id: int, away_team_id: int) -> int:
        """
        Look up player's team_id from the players.json database.

        Only returns team_id if the player belongs to one of the two teams in this game.
        """
        try:
            import json
            import os

            # Load players.json database
            players_file = os.path.join(os.path.dirname(__file__), '../../data/players.json')
            if not os.path.exists(players_file):
                return None

            with open(players_file, 'r') as f:
                players_data = json.load(f)

            # Search for player by name
            for player in players_data.get('players', []):
                first_name = player.get('first_name', '')
                last_name = player.get('last_name', '')
                full_name = f"{first_name} {last_name}".strip()

                # Match by full name
                if full_name == player_name:
                    player_team_id = player.get('team_id')

                    # Only return if player belongs to one of the teams in this game
                    if player_team_id in [home_team_id, away_team_id]:
                        self.logger.info(f"🔍 Found {player_name} in players database: Team {player_team_id}")
                        return player_team_id
                    else:
                        self.logger.warning(f"⚠️ Player {player_name} belongs to Team {player_team_id}, not in this game ({home_team_id} vs {away_team_id})")
                        return None

            # Player not found in database
            return None

        except Exception as e:
            self.logger.warning(f"Failed to lookup player {player_name} in database: {e}")
            return None

    def _process_full_game_impact(self, game_result: GameResult, context: ProcessingContext, 
                                processing_result: ProcessingResult) -> None:
        """Process game with full season progression impact"""
        
        # 1. Update Standings
        if self.config.update_standings and game_result.requires_standings_update():
            self._update_standings(game_result, context, processing_result)
        
        # 2. Process Player Statistics
        self.logger.info(f"🔍 Player stats config: update_player_stats={self.config.update_player_stats}, requires_updates={game_result.requires_player_stat_updates()}")
        if self.config.update_player_stats and game_result.requires_player_stat_updates():
            self.logger.info(f"🔍 Calling _update_player_statistics...")
            self._update_player_statistics(game_result, context, processing_result)
        else:
            self.logger.warning(f"⚠️ Skipping player statistics update: config={self.config.update_player_stats}, requires={game_result.requires_player_stat_updates()}")
        
        # 3. Process Injuries
        if self.config.process_injuries and game_result.requires_injury_processing():
            self._process_injuries(game_result, context, processing_result)
        
        # 4. Update Team Momentum and Chemistry
        if self.config.update_chemistry:
            self._update_team_momentum(game_result, context, processing_result)
        
        # 5. Analyze Playoff Implications
        self._analyze_playoff_implications(game_result, context, processing_result)
        
        # 6. Record Game History
        self._record_game_history(game_result, context, processing_result)
        
        # 7. Update Team Performance Metrics
        self._update_team_metrics(game_result, context, processing_result)
    
    def _process_statistics_only(self, game_result: GameResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process game for statistics collection only"""
        
        # Collect basic game statistics
        processing_result.add_statistic("game_final_score", game_result.get_final_score_string())
        processing_result.add_statistic("total_plays", game_result.total_plays)
        processing_result.add_statistic("total_drives", game_result.total_drives)
        processing_result.add_statistic("game_duration", game_result.game_duration_minutes)
        
        # Team statistics
        for team_id, team_stats in game_result.team_stats.items():
            team_prefix = f"team_{team_id}"
            processing_result.add_statistic(f"{team_prefix}_score", team_stats.score)
            processing_result.add_statistic(f"{team_prefix}_total_yards", team_stats.total_yards)
            processing_result.add_statistic(f"{team_prefix}_turnovers", team_stats.turnovers)
            processing_result.add_statistic(f"{team_prefix}_penalties", team_stats.penalties)
        
        # Player statistics summary
        processing_result.add_statistic("players_with_stats", len(game_result.player_stats))
        if game_result.player_stats:
            total_touchdowns = sum(p.get_total_touchdowns() for p in game_result.player_stats)
            processing_result.add_statistic("total_touchdowns_scored", total_touchdowns)
        
        processing_result.teams_updated = game_result.teams_affected
    
    def _update_standings(self, game_result: GameResult, context: ProcessingContext,
                         processing_result: ProcessingResult) -> None:
        """Update team standings based on game outcome"""
        
        # Get store manager from config
        store_manager = getattr(self.config, 'store_manager', None)

        if store_manager and store_manager.standings_store:
            try:
                # Use the StandingsStore to actually update standings
                store_manager.standings_store.update_from_game_result(game_result)
                
                # Log what was updated
                if game_result.is_tie_game():
                    processing_result.add_side_effect(f"✅ Standings: Tie game recorded - Team {game_result.away_team_id} vs Team {game_result.home_team_id}")
                else:
                    winner_id = game_result.get_winner_id()
                    loser_id = game_result.get_loser_id()
                    processing_result.add_side_effect(f"✅ Standings: Team {winner_id} defeats Team {loser_id}")
                
                # Track state changes for logging (but actual updates happened in store)
                processing_result.add_state_change("standings_updated", True)
                processing_result.add_state_change("teams_affected", [game_result.home_team_id, game_result.away_team_id])
                
            except Exception as e:
                error_msg = f"❌ Failed to update standings: {str(e)}"
                processing_result.add_side_effect(error_msg)
                processing_result.add_state_change("standings_update_error", str(e))
                
        else:
            # Fallback - log what WOULD happen but don't actually update
            if game_result.is_tie_game():
                processing_result.add_side_effect("⚠️ Would update: Tie game recorded (no store manager)")
            else:
                winner_id = game_result.get_winner_id()
                loser_id = game_result.get_loser_id()
                processing_result.add_side_effect(f"⚠️ Would update: Team {winner_id} defeats Team {loser_id} (no store manager)")
                
            # Log that we don't have store manager access
            processing_result.add_side_effect("⚠️ No store manager - standings not updated")
            processing_result.add_state_change("standings_updated", False)
    
    def _update_player_statistics(self, game_result: GameResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Update individual player season statistics"""

        # DEBUG: Log entry to this method
        self.logger.info(f"🔍 _update_player_statistics called with {len(game_result.player_stats)} player stats")

        # Generate game_id for store persistence (matching DailyDataPersister expectations)
        season_year = getattr(context, 'season_year', context.current_date.year)
        week_num = getattr(context, 'season_week', 1)
        home_team = game_result.home_team_id
        away_team = game_result.away_team_id
        game_id = f"{season_year}_week{week_num}_{home_team}_{away_team}"

        self.logger.info(f"🔍 Generated game_id: {game_id}")

        # Store player statistics in player_stats_store for persistence (following standings pattern)
        store_manager = getattr(self.config, 'store_manager', None)
        self.logger.info(f"🔍 Store manager available: {store_manager is not None}")

        if store_manager and hasattr(store_manager, 'player_stats_store'):
            self.logger.info(f"🔍 Player stats store available: {hasattr(store_manager, 'player_stats_store')}")
            try:
                # Store the complete list of player stats for this game
                store_manager.player_stats_store.data[game_id] = game_result.player_stats
                processing_result.add_statistic("stored_player_stats_count", len(game_result.player_stats))
                processing_result.add_statistic("game_id_for_stats", game_id)
                processing_result.add_side_effect(f"✅ Player Stats: Stored {len(game_result.player_stats)} player stats for game {game_id}")
                self.logger.info(f"✅ Successfully stored {len(game_result.player_stats)} player stats for game {game_id}")
            except Exception as e:
                error_msg = f"❌ Failed to store player statistics: {str(e)}"
                processing_result.add_side_effect(error_msg)
                processing_result.add_state_change("player_stats_store_error", str(e))
                self.logger.error(f"❌ Failed to store player statistics: {e}")
        else:
            # Fallback - log what WOULD happen but don't actually store
            processing_result.add_side_effect("⚠️ No store manager - player statistics not stored")
            processing_result.add_state_change("player_stats_stored", False)
            self.logger.warning(f"⚠️ No store manager available, cannot store player statistics")

        updated_players = 0
        significant_performances = 0
        
        for player_stats in game_result.player_stats:
            player_key = f"player_{player_stats.player_name}"
            
            # Update cumulative season stats
            processing_result.add_state_change(f"{player_key}_games_played", 1)
            
            # Offensive statistics
            if player_stats.passing_yards > 0:
                processing_result.add_state_change(f"{player_key}_season_passing_yards", player_stats.passing_yards)
                processing_result.add_state_change(f"{player_key}_season_passing_tds", player_stats.passing_tds)
            
            if player_stats.rushing_yards > 0:
                processing_result.add_state_change(f"{player_key}_season_rushing_yards", player_stats.rushing_yards)
                processing_result.add_state_change(f"{player_key}_season_rushing_tds", player_stats.rushing_tds)
            
            if player_stats.receiving_yards > 0:
                processing_result.add_state_change(f"{player_key}_season_receiving_yards", player_stats.receiving_yards)
                processing_result.add_state_change(f"{player_key}_season_receiving_tds", player_stats.receiving_tds)
            
            # Check for significant performances
            total_yards = player_stats.get_total_yards()
            total_tds = player_stats.get_total_touchdowns()
            
            if total_yards >= 100 or total_tds >= 2:
                significant_performances += 1
                processing_result.add_side_effect(f"Significant performance: {player_stats.player_name} - {total_yards} yards, {total_tds} TDs")
            
            updated_players += 1
        
        processing_result.add_statistic("players_updated", updated_players)
        processing_result.add_statistic("significant_performances", significant_performances)
    
    def _process_injuries(self, game_result: GameResult, context: ProcessingContext,
                         processing_result: ProcessingResult) -> None:
        """Process player injuries from the game"""
        
        injuries_processed = 0
        serious_injuries = 0
        
        for injury in game_result.state_changes.player_injuries:
            player_name = injury.get("player_name", "Unknown")
            injury_type = injury.get("injury_type", "General")
            severity = injury.get("severity", "Minor")
            weeks_out = injury.get("weeks_out", 1)
            
            # Update player injury status
            injury_key = f"player_{player_name}_injury"
            processing_result.add_state_change(f"{injury_key}_type", injury_type)
            processing_result.add_state_change(f"{injury_key}_severity", severity)
            processing_result.add_state_change(f"{injury_key}_weeks_remaining", weeks_out)
            processing_result.add_state_change(f"{injury_key}_injured_date", context.current_date.isoformat())
            
            # Track for statistics
            injuries_processed += 1
            if severity in ["moderate", "major"] and weeks_out >= 2:
                serious_injuries += 1
                processing_result.add_side_effect(f"Serious injury: {player_name} - {injury_type} ({severity}) - {weeks_out} weeks")
            else:
                processing_result.add_side_effect(f"Minor injury: {player_name} - {injury_type}")
        
        processing_result.add_statistic("injuries_processed", injuries_processed)
        processing_result.add_statistic("serious_injuries", serious_injuries)
    
    def _update_team_momentum(self, game_result: GameResult, context: ProcessingContext,
                            processing_result: ProcessingResult) -> None:
        """Update team momentum and morale based on game outcome"""
        
        # Process momentum changes from the game result
        for team_id, momentum_delta in game_result.state_changes.team_momentum_changes.items():
            processing_result.add_state_change(f"team_{team_id}_momentum", momentum_delta)
            
            if abs(momentum_delta) >= 5.0:
                direction = "positive" if momentum_delta > 0 else "negative"
                processing_result.add_side_effect(f"Significant {direction} momentum shift for Team {team_id}: {momentum_delta:+.1f}")
        
        # Calculate momentum based on game outcome if not explicitly set
        if not game_result.state_changes.team_momentum_changes and not game_result.is_tie_game():
            winner_id = game_result.get_winner_id()
            loser_id = game_result.get_loser_id()
            
            # Winner gets positive momentum, loser gets negative
            winner_momentum = 3.0  # Base momentum gain
            loser_momentum = -2.0  # Base momentum loss
            
            # Adjust based on score differential
            score_diff = abs(game_result.away_score - game_result.home_score)
            if score_diff >= 21:  # Blowout
                winner_momentum += 2.0
                loser_momentum -= 2.0
                processing_result.add_side_effect(f"Blowout victory increases momentum impact")
            elif score_diff <= 3:  # Close game
                winner_momentum += 1.0  # Close wins are valuable
                processing_result.add_side_effect(f"Close victory provides momentum boost")
            
            processing_result.add_state_change(f"team_{winner_id}_momentum", winner_momentum)
            processing_result.add_state_change(f"team_{loser_id}_momentum", loser_momentum)
    
    def _analyze_playoff_implications(self, game_result: GameResult, context: ProcessingContext,
                                    processing_result: ProcessingResult) -> None:
        """Analyze playoff implications of this game"""
        
        # Add playoff implications from game result
        for implication in game_result.state_changes.playoff_implications:
            processing_result.add_side_effect(f"Playoff implication: {implication}")
        
        # Add general playoff context based on week
        if context.season_week >= 15:  # Late season games
            processing_result.add_side_effect(f"Late season game (Week {context.season_week}) - playoff implications heightened")
        
        if context.season_phase == "playoffs":
            processing_result.add_side_effect(f"Playoff game - elimination implications")
        
        # Record divisional game implications if teams are from same division
        # (This would require division information in context)
        processing_result.add_statistic("playoff_context_analyzed", True)
    
    def _record_game_history(self, game_result: GameResult, context: ProcessingContext,
                           processing_result: ProcessingResult) -> None:
        """Record game in historical records"""
        
        # Store game summary for historical reference
        game_summary = {
            "date": context.current_date.isoformat(),
            "week": game_result.week,
            "season_type": game_result.season_type,
            "away_team": game_result.away_team_id,
            "home_team": game_result.home_team_id,
            "final_score": f"{game_result.away_score}-{game_result.home_score}",
            "winner": game_result.get_winner_id(),
            "total_plays": game_result.total_plays,
            "game_duration": game_result.game_duration_minutes
        }
        
        processing_result.add_state_change("game_history_entry", game_summary)
        processing_result.add_statistic("historical_game_recorded", True)
        
        # Record any notable achievements or milestones
        if game_result.key_plays:
            processing_result.add_state_change("game_key_plays", game_result.key_plays)
        
        if game_result.turning_points:
            processing_result.add_state_change("game_turning_points", game_result.turning_points)
    
    def _update_team_metrics(self, game_result: GameResult, context: ProcessingContext,
                           processing_result: ProcessingResult) -> None:
        """Update advanced team performance metrics"""
        
        for team_id, team_stats in game_result.team_stats.items():
            team_prefix = f"team_{team_id}_metrics"
            
            # Efficiency metrics
            if team_stats.third_down_attempts > 0:
                third_down_pct = team_stats.get_third_down_percentage()
                processing_result.add_state_change(f"{team_prefix}_third_down_efficiency", third_down_pct)
            
            if team_stats.red_zone_attempts > 0:
                red_zone_pct = team_stats.get_red_zone_percentage()
                processing_result.add_state_change(f"{team_prefix}_red_zone_efficiency", red_zone_pct)
            
            # Turnover differential impact
            processing_result.add_state_change(f"{team_prefix}_turnovers", team_stats.turnovers)
            
            # Penalty discipline
            penalty_rate = team_stats.penalty_yards / max(1, game_result.total_plays)
            processing_result.add_state_change(f"{team_prefix}_penalty_rate", penalty_rate)
        
        processing_result.add_statistic("team_metrics_updated", True)
    
    def supports_strategy(self, strategy: ProcessingStrategy) -> bool:
        """GameProcessor supports all strategies"""
        return strategy in [
            ProcessingStrategy.STATISTICS_ONLY,
            ProcessingStrategy.FULL_PROGRESSION, 
            ProcessingStrategy.GAME_SIMULATION,
            ProcessingStrategy.CUSTOM
        ]