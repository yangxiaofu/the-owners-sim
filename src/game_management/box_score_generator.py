"""
Box Score Generator

Converts accumulated player statistics into readable NFL-style box scores.
Formats player statistics in traditional box score format for end-of-game reporting.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.play_engine.simulation.stats import PlayerStatsAccumulator, PlayerStats, TeamStatsAccumulator
from src.team_management.teams.team_loader import Team


@dataclass
class BoxScoreSection:
    """A section of the box score (passing, rushing, receiving, etc.)"""
    title: str
    headers: List[str] 
    rows: List[List[str]]
    footnotes: List[str] = None


@dataclass
class TeamBoxScore:
    """Complete box score for one team"""
    team: Team
    sections: List[BoxScoreSection]
    team_totals: Dict[str, str]


class BoxScoreGenerator:
    """
    Generates NFL-style box scores from accumulated player statistics.
    
    Creates formatted box scores with traditional sections:
    - Passing (QB stats)
    - Rushing (RB/QB rushing stats) 
    - Receiving (WR/TE/RB receiving stats)
    - Defense (tackles, sacks, interceptions)
    - Special Teams (kicking stats)
    """
    
    def __init__(self):
        """Initialize box score generator"""
        pass
    
    def generate_team_box_score(self, 
                               team: Team, 
                               player_stats: PlayerStatsAccumulator,
                               team_stats: Optional[Dict[str, int]] = None) -> TeamBoxScore:
        """
        Generate complete box score for a team
        
        Args:
            team: Team object with metadata
            player_stats: Accumulated player statistics
            team_stats: Optional team-level statistics
            
        Returns:
            TeamBoxScore with all formatted sections
        """
        sections = []
        
        # Generate each section of the box score
        sections.append(self._generate_passing_section(player_stats))
        sections.append(self._generate_rushing_section(player_stats))
        sections.append(self._generate_receiving_section(player_stats))
        sections.append(self._generate_defense_section(player_stats))
        sections.append(self._generate_special_teams_section(player_stats))
        
        # Generate team totals
        team_totals = self._generate_team_totals(player_stats, team_stats)
        
        return TeamBoxScore(
            team=team,
            sections=[section for section in sections if section.rows],  # Only include sections with data
            team_totals=team_totals
        )
    
    def _generate_passing_section(self, player_stats: PlayerStatsAccumulator) -> BoxScoreSection:
        """Generate passing statistics section"""
        quarterbacks = [player for player in player_stats.get_all_players_with_stats() 
                       if player.pass_attempts > 0]
        
        headers = ["Player", "C/A", "Yards", "Avg", "TD", "Int", "Sacked", "Rating"]
        rows = []
        
        for qb in quarterbacks:
            completion_pct = (qb.completions / qb.pass_attempts * 100) if qb.pass_attempts > 0 else 0
            avg_yards = (qb.passing_yards / qb.completions) if qb.completions > 0 else 0
            
            # Simplified passer rating calculation (actual NFL formula is complex)
            base_rating = 50.0  # Base rating
            if qb.completions > 0:
                rating = min(158.3, base_rating + (completion_pct * 0.8) + (avg_yards * 2) - (qb.interceptions_thrown * 10))
            else:
                rating = 39.6  # Minimum rating
            
            sacked_display = f"{qb.sacks_taken}-{qb.sack_yards_lost}" if qb.sacks_taken > 0 else "0-0"
            
            rows.append([
                f"{qb.player_name}",
                f"{qb.completions}/{qb.pass_attempts}",
                str(qb.passing_yards),
                f"{avg_yards:.1f}",
                str(qb.passing_tds),
                str(qb.interceptions_thrown),
                sacked_display,
                f"{rating:.1f}"
            ])
        
        return BoxScoreSection(
            title="PASSING",
            headers=headers,
            rows=rows
        )
    
    def _generate_rushing_section(self, player_stats: PlayerStatsAccumulator) -> BoxScoreSection:
        """Generate rushing statistics section"""
        rushers = [player for player in player_stats.get_all_players_with_stats() 
                  if player.carries > 0]
        
        # Sort by rushing yards (descending)
        rushers.sort(key=lambda x: x.rushing_yards, reverse=True)
        
        headers = ["Player", "Carries", "Yards", "Avg", "Long", "TD"]
        rows = []
        
        for rusher in rushers:
            avg_yards = (rusher.rushing_yards / rusher.carries) if rusher.carries > 0 else 0
            
            rows.append([
                f"{rusher.player_name}",
                str(rusher.carries),
                str(rusher.rushing_yards),
                f"{avg_yards:.1f}",
                str(max(0, rusher.rushing_yards)) if rusher.carries == 1 else "N/A",  # Simplified long calculation
                str(rusher.rushing_touchdowns)
            ])
        
        return BoxScoreSection(
            title="RUSHING",
            headers=headers,
            rows=rows
        )
    
    def _generate_receiving_section(self, player_stats: PlayerStatsAccumulator) -> BoxScoreSection:
        """Generate receiving statistics section"""
        receivers = [player for player in player_stats.get_all_players_with_stats() 
                    if player.receptions > 0]
        
        # Sort by receiving yards (descending)
        receivers.sort(key=lambda x: x.receiving_yards, reverse=True)
        
        headers = ["Player", "Rec", "Yards", "Avg", "Long", "TD"]
        rows = []
        
        for receiver in receivers:
            avg_yards = (receiver.receiving_yards / receiver.receptions) if receiver.receptions > 0 else 0
            
            rows.append([
                f"{receiver.player_name}",
                str(receiver.receptions),
                str(receiver.receiving_yards),
                f"{avg_yards:.1f}",
                str(max(0, receiver.receiving_yards)) if receiver.receptions == 1 else "N/A",  # Simplified long calculation
                str(receiver.receiving_tds)
            ])
        
        return BoxScoreSection(
            title="RECEIVING",
            headers=headers,
            rows=rows
        )
    
    def _generate_defense_section(self, player_stats: PlayerStatsAccumulator) -> BoxScoreSection:
        """Generate defensive statistics section"""
        defenders = [player for player in player_stats.get_all_players_with_stats() 
                    if (player.tackles + player.assisted_tackles) > 0 or player.sacks > 0 or player.interceptions > 0]
        
        # Sort by total tackles (solo + assisted)
        defenders.sort(key=lambda x: x.tackles + (x.assisted_tackles * 0.5), reverse=True)
        
        headers = ["Player", "Tackles", "Ast", "Sacks", "TFL", "Int", "PD", "FF"]
        rows = []
        
        for defender in defenders:
            sacks_display = f"{defender.sacks:.1f}" if defender.sacks > 0 else "0"
            
            rows.append([
                f"{defender.player_name}",
                str(defender.tackles),
                str(defender.assisted_tackles),
                sacks_display,
                str(defender.tackles_for_loss),
                str(defender.interceptions),
                str(defender.passes_defended),
                str(defender.forced_fumbles)
            ])
        
        return BoxScoreSection(
            title="DEFENSE",
            headers=headers,
            rows=rows
        )
    
    def _generate_special_teams_section(self, player_stats: PlayerStatsAccumulator) -> BoxScoreSection:
        """Generate special teams statistics section"""
        special_teams = [player for player in player_stats.get_all_players_with_stats() 
                        if player.field_goal_attempts > 0 or player.field_goals_made > 0]
        
        headers = ["Player", "FG Made/Att", "Long", "XP Made/Att", "Punts", "Avg"]
        rows = []
        
        for kicker in special_teams:
            fg_display = f"{kicker.field_goals_made}/{kicker.field_goal_attempts}" if kicker.field_goal_attempts > 0 else "0/0"
            long_fg = str(kicker.longest_field_goal) if kicker.longest_field_goal > 0 else "0"
            
            # Note: Punt stats and XP stats would need to be added to PlayerStats for complete special teams
            rows.append([
                f"{kicker.player_name}",
                fg_display,
                long_fg,
                "N/A",  # XP stats not currently tracked
                "N/A",  # Punt stats not currently tracked
                "N/A"   # Punt average not currently tracked
            ])
        
        return BoxScoreSection(
            title="SPECIAL TEAMS",
            headers=headers,
            rows=rows,
            footnotes=["* Punt and XP statistics not currently implemented in simulation"]
        )
    
    def _generate_team_totals(self, 
                             player_stats: PlayerStatsAccumulator, 
                             team_stats: Optional[Dict[str, int]] = None) -> Dict[str, str]:
        """Generate team-level totals from player statistics"""
        all_players = player_stats.get_all_players_with_stats()
        
        # Calculate totals from player stats
        total_passing_yards = sum(p.passing_yards for p in all_players)  # Gross passing yards
        total_rushing_yards = sum(p.rushing_yards for p in all_players)
        
        # Calculate sack statistics
        total_sacks_taken = sum(p.sacks_taken for p in all_players)
        total_sack_yards_lost = sum(p.sack_yards_lost for p in all_players)
        
        # NFL Standard: Net passing yards = gross passing - sack yards
        net_passing_yards = total_passing_yards - total_sack_yards_lost
        
        # Total yards uses net passing yards (NFL standard)
        total_yards = net_passing_yards + total_rushing_yards
        
        total_pass_attempts = sum(p.pass_attempts for p in all_players)
        total_completions = sum(p.completions for p in all_players)
        
        total_penalties = sum(p.penalties for p in all_players)
        total_penalty_yards = sum(p.penalty_yards for p in all_players)
        
        # Format passing yards to show both net and gross
        if total_sack_yards_lost > 0:
            passing_display = f"{net_passing_yards} net ({total_passing_yards} gross - {total_sack_yards_lost} sacks)"
        else:
            passing_display = str(total_passing_yards)
        
        totals = {
            "Total Yards": str(total_yards),
            "Passing Yards": passing_display,
            "Rushing Yards": str(total_rushing_yards),
            "Pass Attempts": str(total_pass_attempts),
            "Completions": str(total_completions),
            "Sacks Allowed": f"{total_sacks_taken}-{total_sack_yards_lost}" if total_sacks_taken > 0 else "0-0",
            "Penalties": f"{total_penalties}-{total_penalty_yards}" if total_penalties > 0 else "0-0"
        }
        
        # Add team stats if provided
        if team_stats:
            for key, value in team_stats.items():
                if key not in totals:  # Don't override calculated values
                    totals[key.replace('_', ' ').title()] = str(value)
        
        return totals
    
    def format_box_score(self, team_box_score: TeamBoxScore) -> str:
        """
        Format team box score as readable text
        
        Args:
            team_box_score: TeamBoxScore to format
            
        Returns:
            Formatted string representation of the box score
        """
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append(f"{team_box_score.team.full_name.upper()} BOX SCORE")
        lines.append('=' * 60)
        
        for section in team_box_score.sections:
            if not section.rows:  # Skip empty sections
                continue
                
            lines.append(f"\n{section.title}")
            lines.append('-' * 60)
            
            # Format headers
            header_line = ""
            col_widths = [15, 8, 8, 6, 6, 4, 8, 8]  # Adjust based on content
            
            for i, header in enumerate(section.headers):
                width = col_widths[i] if i < len(col_widths) else 8
                header_line += f"{header:<{width}}"
            lines.append(header_line)
            
            # Format data rows
            for row in section.rows:
                row_line = ""
                for i, cell in enumerate(row):
                    width = col_widths[i] if i < len(col_widths) else 8
                    row_line += f"{cell:<{width}}"
                lines.append(row_line)
            
            # Add footnotes if any
            if section.footnotes:
                for footnote in section.footnotes:
                    lines.append(footnote)
        
        # Add team totals
        if team_box_score.team_totals:
            lines.append(f"\nTEAM TOTALS")
            lines.append('-' * 60)
            for key, value in team_box_score.team_totals.items():
                lines.append(f"{key:<25} {value}")
        
        lines.append('=' * 60)
        return '\n'.join(lines)
    
    def generate_combined_box_score(self, 
                                   home_team: Team,
                                   away_team: Team,
                                   home_player_stats: PlayerStatsAccumulator,
                                   away_player_stats: PlayerStatsAccumulator,
                                   final_score: Dict[str, int],
                                   home_team_stats: Optional[Dict[str, int]] = None,
                                   away_team_stats: Optional[Dict[str, int]] = None) -> str:
        """
        Generate combined box score for both teams
        
        Args:
            home_team: Home team object
            away_team: Away team object  
            home_player_stats: Home team player statistics
            away_player_stats: Away team player statistics
            final_score: Final score dictionary
            home_team_stats: Optional home team statistics
            away_team_stats: Optional away team statistics
            
        Returns:
            Formatted string with complete game box score
        """
        lines = []
        
        # Game header
        lines.append(f"\n{'*' * 80}")
        lines.append(f"FINAL BOX SCORE: {away_team.full_name} @ {home_team.full_name}")
        lines.append(f"FINAL SCORE: {away_team.abbreviation} {final_score[away_team.full_name]} - {home_team.abbreviation} {final_score[home_team.full_name]}")
        lines.append('*' * 80)
        
        # Generate box scores for both teams
        away_box_score = self.generate_team_box_score(away_team, away_player_stats, away_team_stats)
        home_box_score = self.generate_team_box_score(home_team, home_player_stats, home_team_stats)
        
        # Format away team box score
        lines.append(self.format_box_score(away_box_score))
        
        # Format home team box score  
        lines.append(self.format_box_score(home_box_score))
        
        return '\n'.join(lines)