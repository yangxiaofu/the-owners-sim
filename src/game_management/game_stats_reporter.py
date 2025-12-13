"""
Game Statistics Reporter

Comprehensive end-of-game statistics reporting system. Combines scoreboard data,
player statistics, team statistics, and drive summaries into complete game reports.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from game_management.game_manager import GameManager, GameState
from game_management.scoreboard import Scoreboard, ScoringEvent
from game_management.box_score_generator import BoxScoreGenerator
from game_management.play_by_play_display import PlayByPlayDisplay, DriveDisplay
from play_engine.simulation.stats import PlayerStatsAccumulator, TeamStatsAccumulator
from team_management.teams.team_loader import Team


@dataclass
class GameSummary:
    """Complete game summary information"""
    home_team: Team
    away_team: Team
    final_score: Dict[str, int]
    winner: Optional[Team]
    total_plays: int
    total_drives: int
    game_duration: str
    attendance: Optional[int] = None
    weather: Optional[str] = None


@dataclass
class TeamGameStats:
    """Team-level game statistics"""
    team: Team
    points: int
    total_yards: int
    passing_yards: int
    rushing_yards: int
    first_downs: int
    third_down_conversions: str
    fourth_down_conversions: str
    turnovers: int
    penalties: str
    time_of_possession: str
    red_zone_efficiency: str


@dataclass
class ScoringPlay:
    """Individual scoring play information"""
    quarter: int
    time: str
    team: str
    play_description: str
    score_after: str


class GameStatsReporter:
    """
    Comprehensive game statistics reporter.
    
    Generates complete end-of-game reports including:
    - Game summary and final score
    - Team statistics comparison
    - Individual player box scores  
    - Scoring summary
    - Drive summaries
    - Key game moments
    """
    
    def __init__(self):
        """Initialize game statistics reporter"""
        self.box_score_generator = BoxScoreGenerator()
    
    def generate_full_game_report(self, 
                                 game_manager: GameManager,
                                 home_player_stats: PlayerStatsAccumulator,
                                 away_player_stats: PlayerStatsAccumulator,
                                 home_team_stats: Optional[Dict[str, int]] = None,
                                 away_team_stats: Optional[Dict[str, int]] = None,
                                 drive_summaries: Optional[List[DriveDisplay]] = None,
                                 key_moments: Optional[List[str]] = None) -> str:
        """
        Generate complete game report
        
        Args:
            game_manager: GameManager with complete game state
            home_player_stats: Home team player statistics
            away_player_stats: Away team player statistics  
            home_team_stats: Optional home team statistics
            away_team_stats: Optional away team statistics
            drive_summaries: Optional drive summaries
            key_moments: Optional list of key game moments
            
        Returns:
            Complete formatted game report
        """
        lines = []
        
        # Game header and summary
        game_summary = self._generate_game_summary(game_manager)
        lines.append(self._format_game_header(game_summary))
        
        # Final score and winner
        lines.append(self._format_final_score_summary(game_summary))
        
        # Scoring summary
        scoring_summary = self._generate_scoring_summary(game_manager.scoreboard)
        if scoring_summary:
            lines.append(scoring_summary)
        
        # Team statistics comparison
        team_stats_comparison = self._generate_team_stats_comparison(
            game_manager, home_team_stats, away_team_stats,
            home_player_stats, away_player_stats
        )
        lines.append(team_stats_comparison)
        
        # Box scores for both teams
        box_scores = self.box_score_generator.generate_combined_box_score(
            game_manager.home_team, game_manager.away_team,
            home_player_stats, away_player_stats,
            game_summary.final_score, home_team_stats, away_team_stats
        )
        lines.append(box_scores)
        
        # Drive summaries
        if drive_summaries:
            lines.append(self._format_drive_summaries(drive_summaries))
        
        # Key moments
        if key_moments:
            lines.append(self._format_key_moments(key_moments))
        
        # Game statistics
        lines.append(self._format_game_statistics(game_manager, home_player_stats, away_player_stats))
        
        return '\n'.join(lines)
    
    def _generate_game_summary(self, game_manager: GameManager) -> GameSummary:
        """Generate high-level game summary"""
        final_score = game_manager.get_final_score()
        winner = game_manager.get_winner()
        game_state = game_manager.get_game_state()
        
        return GameSummary(
            home_team=game_manager.home_team,
            away_team=game_manager.away_team,
            final_score=final_score,
            winner=winner,
            total_plays=game_state.total_plays,
            total_drives=game_state.drives_completed,
            game_duration="3:15"  # Typical NFL game duration
        )
    
    def _generate_scoring_summary(self, scoreboard: Scoreboard) -> str:
        """Generate scoring summary with all scoring plays"""
        scoring_history = scoreboard.get_scoring_history()
        if not scoring_history:
            return ""
        
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append("SCORING SUMMARY")
        lines.append('=' * 60)
        
        # Group by quarter
        quarters = {}
        for event in scoring_history:
            quarter = event.quarter
            if quarter not in quarters:
                quarters[quarter] = []
            quarters[quarter].append(event)
        
        for quarter in sorted(quarters.keys()):
            lines.append(f"\nQUARTER {quarter}")
            lines.append('-' * 20)
            
            for event in quarters[quarter]:
                team_name = f"Team {event.team_id}"  # Would need team lookup
                scoring_type = event.scoring_type.name.replace('_', ' ').title()
                
                lines.append(f"{event.game_time:<8} {team_name} - {scoring_type} ({event.points} pts)")
                if event.description:
                    lines.append(f"         {event.description}")
        
        lines.append('=' * 60)
        return '\n'.join(lines)
    
    def _generate_team_stats_comparison(self, 
                                      game_manager: GameManager,
                                      home_team_stats: Optional[Dict[str, int]],
                                      away_team_stats: Optional[Dict[str, int]],
                                      home_player_stats: PlayerStatsAccumulator,
                                      away_player_stats: PlayerStatsAccumulator) -> str:
        """Generate team statistics comparison table"""
        lines = []
        lines.append(f"\n{'=' * 70}")
        lines.append("TEAM STATISTICS")
        lines.append('=' * 70)
        
        # Calculate team stats from player stats
        home_stats = self._calculate_team_stats_from_players(game_manager.home_team, home_player_stats)
        away_stats = self._calculate_team_stats_from_players(game_manager.away_team, away_player_stats)
        
        # Format comparison table
        lines.append(f"{'Statistic':<25} {game_manager.away_team.abbreviation:>10} {game_manager.home_team.abbreviation:>10}")
        lines.append('-' * 70)
        
        # Compare key statistics
        stat_comparisons = [
            ("Total Yards", home_stats.total_yards, away_stats.total_yards),
            ("Passing Yards", home_stats.passing_yards, away_stats.passing_yards),
            ("Rushing Yards", home_stats.rushing_yards, away_stats.rushing_yards),
            ("First Downs", home_stats.first_downs, away_stats.first_downs),
            ("Turnovers", home_stats.turnovers, away_stats.turnovers),
            ("Penalties", f"{home_stats.penalties.split('-')[0]}", f"{away_stats.penalties.split('-')[0]}"),
            ("Time of Possession", home_stats.time_of_possession, away_stats.time_of_possession)
        ]
        
        for stat_name, home_value, away_value in stat_comparisons:
            lines.append(f"{stat_name:<25} {str(away_value):>10} {str(home_value):>10}")
        
        lines.append('=' * 70)
        return '\n'.join(lines)
    
    def _calculate_team_stats_from_players(self, team: Team, player_stats: PlayerStatsAccumulator) -> TeamGameStats:
        """Calculate team statistics from accumulated player stats"""
        all_players = player_stats.get_all_players_with_stats()
        
        # Calculate passing statistics
        total_passing_yards = sum(p.passing_yards for p in all_players)  # Gross passing yards
        total_sack_yards_lost = sum(p.sack_yards_lost for p in all_players)
        net_passing_yards = total_passing_yards - total_sack_yards_lost  # NFL standard net passing
        
        total_rushing_yards = sum(p.rushing_yards for p in all_players)
        
        # Use net passing yards for total yards (NFL standard)
        total_yards = net_passing_yards + total_rushing_yards
        
        total_penalties = sum(p.penalties for p in all_players)
        total_penalty_yards = sum(p.penalty_yards for p in all_players)
        penalty_display = f"{total_penalties}-{total_penalty_yards}" if total_penalties > 0 else "0-0"
        
        # Calculate turnovers
        interceptions_thrown = sum(p.interceptions_thrown for p in all_players)
        fumbles_lost = 0  # Would need fumble tracking
        total_turnovers = interceptions_thrown + fumbles_lost
        
        return TeamGameStats(
            team=team,
            points=0,  # Would need from scoreboard
            total_yards=total_yards,
            passing_yards=net_passing_yards,  # Use net passing yards for team stats
            rushing_yards=total_rushing_yards,
            first_downs=0,  # Would need tracking
            third_down_conversions="N/A",  # Would need tracking
            fourth_down_conversions="N/A",  # Would need tracking  
            turnovers=total_turnovers,
            penalties=penalty_display,
            time_of_possession="N/A",  # Would need tracking
            red_zone_efficiency="N/A"  # Would need tracking
        )
    
    def _format_game_header(self, game_summary: GameSummary) -> str:
        """Format game header section"""
        lines = []
        lines.append(f"\n{'*' * 80}")
        lines.append(f"NFL GAME SIMULATION - FINAL REPORT")
        lines.append(f"{game_summary.away_team.full_name} @ {game_summary.home_team.full_name}")
        lines.append(f"Game Duration: {game_summary.game_duration}")
        lines.append(f"Total Plays: {game_summary.total_plays} | Total Drives: {game_summary.total_drives}")
        lines.append('*' * 80)
        return '\n'.join(lines)
    
    def _format_final_score_summary(self, game_summary: GameSummary) -> str:
        """Format final score and winner announcement"""
        lines = []
        lines.append(f"\n🏆 FINAL SCORE")
        lines.append('=' * 50)
        
        away_score = game_summary.final_score[game_summary.away_team.full_name]
        home_score = game_summary.final_score[game_summary.home_team.full_name]
        
        lines.append(f"{game_summary.away_team.full_name:<30} {away_score:>3}")
        lines.append(f"{game_summary.home_team.full_name:<30} {home_score:>3}")
        
        if game_summary.winner:
            lines.append(f"\n🎉 WINNER: {game_summary.winner.full_name}")
        else:
            lines.append(f"\n🤝 GAME TIED")
        
        lines.append('=' * 50)
        return '\n'.join(lines)
    
    def _format_drive_summaries(self, drive_summaries: List[DriveDisplay]) -> str:
        """Format all drive summaries"""
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append("DRIVE SUMMARIES")
        lines.append('=' * 60)
        
        for drive in drive_summaries:
            lines.append(f"\nDrive #{drive.drive_number}: {drive.possessing_team}")
            lines.append(f"  {drive.starting_position} → {drive.ending_position} ({drive.drive_result})")
            lines.append(f"  {drive.total_plays} plays, {drive.total_yards:+d} yards")
            
            if drive.key_plays:
                lines.append(f"  Key plays: {', '.join(drive.key_plays[:2])}")
        
        lines.append('=' * 60)
        return '\n'.join(lines)
    
    def _format_key_moments(self, key_moments: List[str]) -> str:
        """Format key game moments"""
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append("KEY GAME MOMENTS")
        lines.append('=' * 60)
        
        for i, moment in enumerate(key_moments, 1):
            lines.append(f"{i}. {moment}")
        
        lines.append('=' * 60)
        return '\n'.join(lines)
    
    def _format_game_statistics(self, 
                               game_manager: GameManager,
                               home_player_stats: PlayerStatsAccumulator,
                               away_player_stats: PlayerStatsAccumulator) -> str:
        """Format additional game statistics"""
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append("GAME STATISTICS")
        lines.append('=' * 60)
        
        # Player participation
        home_players = len(home_player_stats.get_all_players_with_stats())
        away_players = len(away_player_stats.get_all_players_with_stats())
        
        lines.append(f"Players with statistics:")
        lines.append(f"  {game_manager.home_team.full_name}: {home_players} players")
        lines.append(f"  {game_manager.away_team.full_name}: {away_players} players")
        
        # Plays processed
        home_plays = home_player_stats.get_plays_processed()
        away_plays = away_player_stats.get_plays_processed()
        lines.append(f"\nPlays tracked:")
        lines.append(f"  {game_manager.home_team.full_name}: {home_plays} plays")
        lines.append(f"  {game_manager.away_team.full_name}: {away_plays} plays")
        
        # Scoring breakdown
        home_score = game_manager.scoreboard.get_team_score(game_manager.home_team.team_id)
        away_score = game_manager.scoreboard.get_team_score(game_manager.away_team.team_id)
        total_points = home_score + away_score
        
        lines.append(f"\nScoring:")
        lines.append(f"  Total points scored: {total_points}")
        lines.append(f"  Scoring plays: {len(game_manager.scoreboard.get_scoring_history())}")
        
        lines.append('=' * 60)
        return '\n'.join(lines)
    
    def generate_quick_summary(self, game_manager: GameManager) -> str:
        """Generate a quick one-line game summary"""
        final_score = game_manager.get_final_score()
        winner = game_manager.get_winner()
        
        away_score = final_score[game_manager.away_team.full_name]  
        home_score = final_score[game_manager.home_team.full_name]
        
        summary = f"{game_manager.away_team.abbreviation} {away_score} - {home_score} {game_manager.home_team.abbreviation}"
        
        if winner:
            summary += f" (Final - {winner.full_name} wins)"
        else:
            summary += " (Final - Tie)"
        
        return summary
    
    def export_game_data(self, 
                        game_manager: GameManager,
                        home_player_stats: PlayerStatsAccumulator,
                        away_player_stats: PlayerStatsAccumulator) -> Dict:
        """Export game data as structured dictionary for external use"""
        game_state = game_manager.get_game_state()
        
        return {
            "game_info": {
                "home_team": {
                    "name": game_manager.home_team.full_name,
                    "abbreviation": game_manager.home_team.abbreviation,
                    "team_id": game_manager.home_team.team_id
                },
                "away_team": {
                    "name": game_manager.away_team.full_name,
                    "abbreviation": game_manager.away_team.abbreviation,
                    "team_id": game_manager.away_team.team_id
                },
                "final_score": game_manager.get_final_score(),
                "winner": game_manager.get_winner().full_name if game_manager.get_winner() else None
            },
            "statistics": {
                "total_plays": game_state.total_plays,
                "total_drives": game_state.drives_completed,
                "home_players_with_stats": len(home_player_stats.get_all_players_with_stats()),
                "away_players_with_stats": len(away_player_stats.get_all_players_with_stats()),
                "scoring_plays": len(game_manager.scoreboard.get_scoring_history())
            },
            "scoring_history": [
                {
                    "team_id": event.team_id,
                    "scoring_type": event.scoring_type.name,
                    "points": event.points,
                    "quarter": event.quarter,
                    "game_time": event.game_time,
                    "description": event.description
                }
                for event in game_manager.scoreboard.get_scoring_history()
            ]
        }