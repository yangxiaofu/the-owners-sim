"""
Results Display Formatter

Handles terminal formatting for game results, standings, and other demo output.
Provides colorized, table-formatted display suitable for console interfaces.
"""

from typing import Dict, Any, List, Optional
from datetime import date
import sys


class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Standard colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'
    
    # Bright colors
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_CYAN = '\033[96m'


class ResultsDisplayFormatter:
    """
    Formats simulation results for attractive terminal display.
    
    Provides methods to format game results, standings tables,
    season progress, and other demo output with colors and 
    proper alignment.
    """
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize the display formatter.
        
        Args:
            use_colors: Whether to use terminal colors (disable for compatibility)
        """
        self.use_colors = use_colors and sys.stdout.isatty()
        
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_colors:
            return text
        return f"{color}{text}{Colors.RESET}"
    
    def format_week_results(self, week_results: Dict[str, Any]) -> str:
        """
        Format the results from a simulated week.
        
        Args:
            week_results: WeekResults object data
            
        Returns:
            Formatted string ready for terminal display
        """
        week_num = week_results['week_number']
        games = week_results['game_results']
        successful = week_results['successful_games']
        failed = week_results['failed_games']
        
        output = []
        
        # Week header
        header = f"🏈 WEEK {week_num} RESULTS"
        output.append("")
        output.append(self.colorize("=" * len(header), Colors.CYAN))
        output.append(self.colorize(header, Colors.BOLD + Colors.CYAN))
        output.append(self.colorize("=" * len(header), Colors.CYAN))
        output.append("")
        
        if not games:
            output.append(self.colorize("No games played this week.", Colors.YELLOW))
            output.append("")
            return "\n".join(output)
        
        # Games table
        output.append(self._format_games_table(games))
        
        # Week summary
        output.append("")
        summary = f"Week {week_num} Summary: {successful} games completed"
        if failed > 0:
            summary += f", {failed} failed"
        output.append(self.colorize(summary, Colors.BRIGHT_BLUE))
        
        if week_results.get('errors'):
            output.append("")
            output.append(self.colorize("⚠️  Errors:", Colors.YELLOW))
            for error in week_results['errors'][:3]:  # Show max 3 errors
                output.append(f"   • {error}")
        
        output.append("")
        return "\n".join(output)
    
    def _format_games_table(self, games: List[Dict[str, Any]]) -> str:
        """Format games as an aligned table."""
        if not games:
            return ""
        
        output = []
        
        # Table header
        header = f"{'Away Team':<20} {'Score':<7} {'Home Team':<20} {'Result':<10}"
        output.append(self.colorize(header, Colors.BOLD + Colors.WHITE))
        output.append(self.colorize("-" * len(header), Colors.DIM))
        
        # Game rows
        for game in games:
            away_name = self._truncate_team_name(game['away_team_name'])
            home_name = self._truncate_team_name(game['home_team_name'])
            score = f"{game['away_score']}-{game['home_score']}"
            
            # Determine winner and color
            if game['is_tie']:
                result = "TIE"
                result_color = Colors.YELLOW
                winner_color = Colors.YELLOW
            elif game['winner_id'] == game['home_team_id']:
                result = "HOME WIN"
                result_color = Colors.GREEN
                winner_color = Colors.GREEN
                home_name = self.colorize(home_name, Colors.BOLD + Colors.GREEN)
            else:
                result = "AWAY WIN"
                result_color = Colors.GREEN
                winner_color = Colors.GREEN
                away_name = self.colorize(away_name, Colors.BOLD + Colors.GREEN)
            
            # Format score with colors
            score = self.colorize(score, Colors.BRIGHT_YELLOW)
            result = self.colorize(result, result_color)
            
            row = f"{away_name:<30} {score:<15} {home_name:<30} {result:<20}"
            output.append(row)
        
        return "\n".join(output)
    
    def format_standings(self, standings: Optional[Dict[str, Any]]) -> str:
        """
        Format current season standings.
        
        Args:
            standings: Standings data from StandingsStore
            
        Returns:
            Formatted standings table
        """
        if not standings:
            return self.colorize("📊 Standings not available", Colors.YELLOW)
        
        output = []
        
        # Standings header
        header = "📊 CURRENT STANDINGS"
        output.append("")
        output.append(self.colorize("=" * len(header), Colors.BLUE))
        output.append(self.colorize(header, Colors.BOLD + Colors.BLUE))
        output.append(self.colorize("=" * len(header), Colors.BLUE))
        output.append("")
        
        # Format by conference and division
        conferences_data = standings.get('conferences', {})
        divisions_data = standings.get('divisions', {})
        
        for conference in ['AFC', 'NFC']:
            if conference in conferences_data:
                # Get divisions for this conference
                conf_divisions = {}
                for div_name, div_teams in divisions_data.items():
                    if div_name.startswith(conference):
                        # Extract division name (e.g., "AFC East" -> "east")
                        div_key = div_name.replace(f"{conference} ", "").lower()
                        conf_divisions[div_key] = div_teams
                
                if conf_divisions:
                    output.append(self._format_conference_standings(conference, conf_divisions))
                    output.append("")
        
        return "\n".join(output)
    
    def _format_conference_standings(self, conference: str, conf_data: Dict[str, Any]) -> str:
        """Format standings for a single conference."""
        output = []
        
        # Conference header
        conf_header = f"{conference} CONFERENCE"
        output.append(self.colorize(conf_header, Colors.BOLD + Colors.BRIGHT_CYAN))
        output.append(self.colorize("-" * len(conf_header), Colors.CYAN))
        
        # Division standings
        divisions = ['East', 'North', 'South', 'West']
        
        for division in divisions:
            div_key = division.lower()
            if div_key in conf_data:
                output.append("")
                output.append(self._format_division_standings(f"{conference} {division}", conf_data[div_key]))
        
        return "\n".join(output)
    
    def _format_division_standings(self, division_name: str, teams: List[Dict[str, Any]]) -> str:
        """Format standings for a single division."""
        output = []
        
        # Division header
        output.append(self.colorize(f"  {division_name}:", Colors.BRIGHT_BLUE))
        
        # Table header
        header = f"    {'Team':<20} {'W':<3} {'L':<3} {'T':<3} {'PCT':<6} {'PF':<4} {'PA':<4}"
        output.append(self.colorize(header, Colors.BOLD))
        
        # Team rows
        for i, team in enumerate(teams):
            # Handle the actual structure: {'team_id': 1, 'standing': <EnhancedTeamStanding>}
            team_id = team.get('team_id', 0)
            standing = team.get('standing')
            
            # Get team name - use team_id as fallback for now
            team_name = self._get_team_name_from_id(team_id) 
            team_name = self._truncate_team_name(team_name, 18)
            
            # Get stats from standing object
            if standing:
                wins = getattr(standing, 'wins', 0)
                losses = getattr(standing, 'losses', 0) 
                ties = getattr(standing, 'ties', 0)
            else:
                wins = losses = ties = 0
            
            # Calculate win percentage
            total_games = wins + losses + ties
            pct = (wins + 0.5 * ties) / total_games if total_games > 0 else 0.000
            
            # Get points from standing object
            if standing:
                points_for = getattr(standing, 'points_for', 0)
                points_against = getattr(standing, 'points_against', 0)
            else:
                points_for = points_against = 0
            
            # Color first place team
            if i == 0:
                team_name = self.colorize(team_name, Colors.BOLD + Colors.GREEN)
            
            row = f"    {team_name:<28} {wins:<3} {losses:<3} {ties:<3} {pct:<6.3f} {points_for:<4} {points_against:<4}"
            output.append(row)
        
        return "\n".join(output)
    
    def format_season_status(self, status: Dict[str, Any]) -> str:
        """
        Format season progress status.
        
        Args:
            status: Season status dictionary
            
        Returns:
            Formatted status display
        """
        if not status['season_initialized']:
            return self.colorize("⏳ Season not initialized", Colors.YELLOW)
        
        output = []
        
        # Season info
        season_year = status['season_year']
        dynasty = status['dynasty_name']
        current_week = status['current_week']
        weeks_remaining = status['weeks_remaining']
        progress = status['progress_percentage']
        
        # Header
        header = f"📈 SEASON STATUS - {season_year}"
        output.append("")
        output.append(self.colorize(header, Colors.BOLD + Colors.MAGENTA))
        output.append(self.colorize("-" * len(header), Colors.MAGENTA))
        
        # Status details
        output.append(f"Dynasty: {self.colorize(dynasty, Colors.BRIGHT_CYAN)}")
        output.append(f"Current Week: {self.colorize(str(current_week), Colors.BRIGHT_YELLOW)} of 18")
        output.append(f"Weeks Remaining: {self.colorize(str(weeks_remaining), Colors.BRIGHT_BLUE)}")
        output.append(f"Progress: {self.colorize(f'{progress:.1f}%', Colors.BRIGHT_GREEN)}")
        
        # Progress bar
        bar_length = 30
        filled = int((progress / 100.0) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        output.append(f"Progress: [{self.colorize(bar, Colors.GREEN)}]")
        
        if status['season_complete']:
            output.append("")
            output.append(self.colorize("🏆 SEASON COMPLETE!", Colors.BOLD + Colors.GREEN))
        
        output.append("")
        return "\n".join(output)
    
    def format_menu(self, options: List[str], title: str = "Select an option:") -> str:
        """
        Format a menu with numbered options.
        
        Args:
            options: List of menu option strings
            title: Menu title
            
        Returns:
            Formatted menu display
        """
        output = []
        
        output.append("")
        output.append(self.colorize(title, Colors.BOLD + Colors.WHITE))
        output.append("")
        
        for i, option in enumerate(options, 1):
            prefix = self.colorize(f"{i}.", Colors.BRIGHT_CYAN)
            output.append(f"  {prefix} {option}")
        
        output.append("")
        prompt = "Enter your choice: "
        output.append(self.colorize(prompt, Colors.BRIGHT_YELLOW))
        
        return "\n".join(output[:-1]) + "\n" + output[-1]  # No newline after prompt
    
    def format_error(self, message: str) -> str:
        """Format an error message."""
        return self.colorize(f"❌ Error: {message}", Colors.BRIGHT_RED)
    
    def format_info(self, message: str) -> str:
        """Format an info message."""
        return self.colorize(f"ℹ️  {message}", Colors.BRIGHT_BLUE)
    
    def format_success(self, message: str) -> str:
        """Format a success message."""
        return self.colorize(f"✅ {message}", Colors.BRIGHT_GREEN)
    
    def format_warning(self, message: str) -> str:
        """Format a warning message."""
        return self.colorize(f"⚠️  {message}", Colors.BRIGHT_YELLOW)
    
    def _truncate_team_name(self, name: str, max_length: int = 18) -> str:
        """Truncate team name if too long."""
        if len(name) <= max_length:
            return name
        return name[:max_length-3] + "..."
    
    def clear_screen(self) -> str:
        """Return string to clear terminal screen."""
        return "\033[2J\033[H"
    
    def format_header(self, text: str, width: int = 60) -> str:
        """Format a centered header with borders."""
        lines = []
        lines.append(self.colorize("=" * width, Colors.CYAN))
        
        # Center the text
        padding = (width - len(text) - 2) // 2
        centered = f"{' ' * padding}{text}{' ' * (width - len(text) - padding - 2)}"
        lines.append(self.colorize(f"│{centered}│", Colors.BOLD + Colors.CYAN))
        
        lines.append(self.colorize("=" * width, Colors.CYAN))
        return "\n".join(lines)
    
    def _get_team_name_from_id(self, team_id: int) -> str:
        """Get full team name for display using team constants."""
        # Import team data management
        try:
            from scheduling.data.team_data import TeamDataManager
            team_manager = TeamDataManager()
            team = team_manager.get_team(team_id)
            return team.full_name if team else f"Team {team_id}"
        except ImportError:
            # Fallback to basic team ID display
            return f"Team {team_id}"

    def format_passing_leaders(self, leaders: List[Dict[str, Any]]) -> str:
        """
        Format passing statistics leaderboard.

        Args:
            leaders: List of passing leaders from database

        Returns:
            Formatted passing leaderboard table
        """
        if not leaders:
            return self.colorize("📊 No passing statistics available", Colors.YELLOW)

        output = []

        # Header
        header = "🏈 PASSING LEADERS"
        output.append("")
        output.append(self.colorize("=" * len(header), Colors.BLUE))
        output.append(self.colorize(header, Colors.BOLD + Colors.BLUE))
        output.append(self.colorize("=" * len(header), Colors.BLUE))
        output.append("")

        # Table header
        table_header = f"{'RANK':<4} {'PLAYER':<20} {'TEAM':<12} {'YDS':<6} {'TD':<4} {'CMP':<4} {'ATT':<4} {'PCT':<6} {'YPG':<6}"
        output.append(self.colorize(table_header, Colors.BOLD + Colors.WHITE))
        output.append(self.colorize("-" * len(table_header), Colors.DIM))

        # Player rows
        for i, player in enumerate(leaders, 1):
            rank = f"{i}."
            player_name = self._truncate_team_name(player['player_name'], 18)
            team_name = self._get_team_abbreviation(player['team_id'])
            yards = player['total_passing_yards']
            tds = player['total_passing_tds']
            completions = player['total_completions']
            attempts = player['total_attempts']
            pct = f"{player['completion_percentage']:.1f}%"
            ypg = f"{player['avg_yards_per_game']:.1f}"

            # Highlight top 3
            if i <= 3:
                player_name = self.colorize(player_name, Colors.BOLD + Colors.GREEN)
                yards = self.colorize(str(yards), Colors.BRIGHT_YELLOW)

            row = f"{rank:<4} {player_name:<28} {team_name:<12} {str(yards):<6} {tds:<4} {completions:<4} {attempts:<4} {pct:<6} {ypg:<6}"
            output.append(row)

        output.append("")
        return "\n".join(output)

    def format_rushing_leaders(self, leaders: List[Dict[str, Any]]) -> str:
        """
        Format rushing statistics leaderboard.

        Args:
            leaders: List of rushing leaders from database

        Returns:
            Formatted rushing leaderboard table
        """
        if not leaders:
            return self.colorize("📊 No rushing statistics available", Colors.YELLOW)

        output = []

        # Header
        header = "🏃 RUSHING LEADERS"
        output.append("")
        output.append(self.colorize("=" * len(header), Colors.GREEN))
        output.append(self.colorize(header, Colors.BOLD + Colors.GREEN))
        output.append(self.colorize("=" * len(header), Colors.GREEN))
        output.append("")

        # Table header
        table_header = f"{'RANK':<4} {'PLAYER':<20} {'TEAM':<12} {'YDS':<6} {'TD':<4} {'ATT':<4} {'YPC':<6} {'YPG':<6}"
        output.append(self.colorize(table_header, Colors.BOLD + Colors.WHITE))
        output.append(self.colorize("-" * len(table_header), Colors.DIM))

        # Player rows
        for i, player in enumerate(leaders, 1):
            rank = f"{i}."
            player_name = self._truncate_team_name(player['player_name'], 18)
            team_name = self._get_team_abbreviation(player['team_id'])
            yards = player['total_rushing_yards']
            tds = player['total_rushing_tds']
            attempts = player['total_attempts']
            ypc = f"{player['yards_per_carry']:.1f}"
            ypg = f"{player['avg_yards_per_game']:.1f}"

            # Highlight top 3
            if i <= 3:
                player_name = self.colorize(player_name, Colors.BOLD + Colors.GREEN)
                yards = self.colorize(str(yards), Colors.BRIGHT_YELLOW)

            row = f"{rank:<4} {player_name:<28} {team_name:<12} {str(yards):<6} {tds:<4} {attempts:<4} {ypc:<6} {ypg:<6}"
            output.append(row)

        output.append("")
        return "\n".join(output)

    def format_receiving_leaders(self, leaders: List[Dict[str, Any]]) -> str:
        """
        Format receiving statistics leaderboard.

        Args:
            leaders: List of receiving leaders from database

        Returns:
            Formatted receiving leaderboard table
        """
        if not leaders:
            return self.colorize("📊 No receiving statistics available", Colors.YELLOW)

        output = []

        # Header
        header = "🙌 RECEIVING LEADERS"
        output.append("")
        output.append(self.colorize("=" * len(header), Colors.MAGENTA))
        output.append(self.colorize(header, Colors.BOLD + Colors.MAGENTA))
        output.append(self.colorize("=" * len(header), Colors.MAGENTA))
        output.append("")

        # Table header
        table_header = f"{'RANK':<4} {'PLAYER':<20} {'TEAM':<12} {'YDS':<6} {'TD':<4} {'REC':<4} {'TGT':<4} {'YPR':<6} {'YPG':<6}"
        output.append(self.colorize(table_header, Colors.BOLD + Colors.WHITE))
        output.append(self.colorize("-" * len(table_header), Colors.DIM))

        # Player rows
        for i, player in enumerate(leaders, 1):
            rank = f"{i}."
            player_name = self._truncate_team_name(player['player_name'], 18)
            team_name = self._get_team_abbreviation(player['team_id'])
            yards = player['total_receiving_yards']
            tds = player['total_receiving_tds']
            receptions = player['total_receptions']
            targets = player['total_targets']
            ypr = f"{player['yards_per_reception']:.1f}"
            ypg = f"{player['avg_yards_per_game']:.1f}"

            # Highlight top 3
            if i <= 3:
                player_name = self.colorize(player_name, Colors.BOLD + Colors.GREEN)
                yards = self.colorize(str(yards), Colors.BRIGHT_YELLOW)

            row = f"{rank:<4} {player_name:<28} {team_name:<12} {str(yards):<6} {tds:<4} {receptions:<4} {targets:<4} {ypr:<6} {ypg:<6}"
            output.append(row)

        output.append("")
        return "\n".join(output)

    def _get_team_abbreviation(self, team_id: int) -> str:
        """Get team abbreviation for display."""
        try:
            from scheduling.data.team_data import TeamDataManager
            team_manager = TeamDataManager()
            team = team_manager.get_team(team_id)
            return team.abbreviation if team else f"T{team_id}"
        except ImportError:
            return f"T{team_id}"