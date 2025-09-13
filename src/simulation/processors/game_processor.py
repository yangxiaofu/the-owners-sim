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
        """Check if this is a GameResult"""
        return isinstance(result, GameResult)
    
    def process_result(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """Process game result with comprehensive season impact"""
        if not isinstance(result, GameResult):
            return ProcessingResult(
                processed_successfully=False,
                processing_type="GameResultProcessor",
                error_messages=["Expected GameResult but received different type"]
            )
        
        game_result: GameResult = result
        processing_result = ProcessingResult(
            processed_successfully=True,
            processing_type="GameResultProcessor"
        )
        
        # Process based on configured strategy
        if self.config.strategy == ProcessingStrategy.STATISTICS_ONLY:
            self._process_statistics_only(game_result, context, processing_result)
        else:
            self._process_full_game_impact(game_result, context, processing_result)
        
        return processing_result
    
    def _process_full_game_impact(self, game_result: GameResult, context: ProcessingContext, 
                                processing_result: ProcessingResult) -> None:
        """Process game with full season progression impact"""
        
        # 1. Update Standings
        if self.config.update_standings and game_result.requires_standings_update():
            self._update_standings(game_result, context, processing_result)
        
        # 2. Process Player Statistics
        if self.config.update_player_stats and game_result.requires_player_stat_updates():
            self._update_player_statistics(game_result, context, processing_result)
        
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
        
        if game_result.is_tie_game():
            # Handle tie game
            for team_id in [game_result.away_team_id, game_result.home_team_id]:
                processing_result.add_state_change(f"team_{team_id}_ties", 1)
            processing_result.add_side_effect(f"Tie game: both teams receive tie in standings")
        
        else:
            winner_id = game_result.get_winner_id()
            loser_id = game_result.get_loser_id()
            
            # Update winner record
            processing_result.add_state_change(f"team_{winner_id}_wins", 1)
            processing_result.add_state_change(f"team_{winner_id}_win_streak", 1)
            processing_result.add_state_change(f"team_{loser_id}_win_streak", 0)  # Reset streak
            
            # Update loser record
            processing_result.add_state_change(f"team_{loser_id}_losses", 1)
            
            # Division/conference record updates if we have that context
            processing_result.add_side_effect(f"Standings updated: Team {winner_id} defeats Team {loser_id}")
        
        # Update head-to-head records
        h2h_key = f"h2h_{min(game_result.away_team_id, game_result.home_team_id)}_{max(game_result.away_team_id, game_result.home_team_id)}"
        processing_result.add_state_change(f"{h2h_key}_last_winner", game_result.get_winner_id())
    
    def _update_player_statistics(self, game_result: GameResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Update individual player season statistics"""
        
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