"""
Terminal Display Utilities for Interactive Season Simulator

Provides formatted display functions for better terminal UX including
banners, status displays, menus, game results, standings tables, and
progress indicators.
"""

from typing import Dict, List, Any, Optional
from datetime import date


# ANSI Color Codes for Terminal Output
class Colors:
    """ANSI color codes for terminal styling"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'

    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


def print_banner() -> None:
    """
    Display ASCII art banner for the interactive season simulator.

    Shows the application title with styled formatting for visual appeal.
    """
    banner = f"""
{Colors.BOLD}{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              NFL INTERACTIVE SEASON SIMULATOR                    ║
║                                                                  ║
║              The Owner's Sim - Dynasty Edition                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def print_status(controller: Any) -> None:
    """
    Show current simulation status including date, week, games played, and phase.

    Args:
        controller: The simulation controller with calendar and state information

    Displays:
        - Current simulation date
        - Current NFL week
        - Total games played
        - Current season phase (Preseason, Regular Season, Playoffs, Offseason)
    """
    try:
        current_date = controller.calendar.get_current_date()
        current_phase = controller.calendar.get_current_phase()
        current_week = controller.calendar.get_current_week()
        games_played = getattr(controller, 'games_played', 0)

        print(f"\n{Colors.BOLD}{Colors.CYAN}═══ SIMULATION STATUS ═══{Colors.RESET}")
        print(f"📅 Date: {Colors.BOLD}{current_date}{Colors.RESET}")
        print(f"📊 Week: {Colors.BOLD}Week {current_week}{Colors.RESET}")
        print(f"🏈 Games Played: {Colors.BOLD}{games_played}{Colors.RESET}")
        print(f"⚡ Phase: {Colors.BOLD}{Colors.YELLOW}{current_phase.value}{Colors.RESET}")
        print(f"{Colors.CYAN}{'═' * 40}{Colors.RESET}\n")

    except Exception as e:
        print(f"{Colors.RED}Error displaying status: {e}{Colors.RESET}")


def print_menu() -> None:
    """
    Display interactive command menu with available options.

    Shows all available commands for controlling the season simulation:
    - 1: Simulate one day
    - 2: Simulate one week
    - 3: Simulate to end of season
    - 4: View standings
    - 5: View upcoming games
    - 0: Exit
    """
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_YELLOW}╔═══ COMMAND MENU ═══╗{Colors.RESET}")
    print(f"{Colors.YELLOW}║{Colors.RESET}  1️⃣  Simulate 1 Day")
    print(f"{Colors.YELLOW}║{Colors.RESET}  2️⃣  Simulate 1 Week")
    print(f"{Colors.YELLOW}║{Colors.RESET}  3️⃣  Simulate to End of Season")
    print(f"{Colors.YELLOW}║{Colors.RESET}  4️⃣  View Standings")
    print(f"{Colors.YELLOW}║{Colors.RESET}  5️⃣  View Upcoming Games")
    print(f"{Colors.YELLOW}║{Colors.RESET}  0️⃣  Exit")
    print(f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}╚════════════════════╝{Colors.RESET}\n")


def display_daily_results(result: Dict[str, Any]) -> None:
    """
    Format and display results from a single day's simulation.

    Args:
        result: Dictionary containing day simulation results with keys:
            - games_played: Number of games simulated
            - game_results: List of game result details
            - current_date: Date of simulation
            - phase: Current season phase

    Displays:
        - Number of games played
        - Score summary for each game
        - Notable statistics or highlights
    """
    if not result or not result.get('games_played', 0):
        print(f"{Colors.DIM}No games scheduled for this day{Colors.RESET}")
        return

    games_played = result.get('games_played', 0)
    game_results = result.get('game_results', [])

    print(f"\n{Colors.BOLD}{Colors.GREEN}═══ DAILY RESULTS ═══{Colors.RESET}")
    print(f"🏈 Games Today: {Colors.BOLD}{games_played}{Colors.RESET}\n")

    for idx, game in enumerate(game_results, 1):
        away_team = game.get('away_team', 'Unknown')
        home_team = game.get('home_team', 'Unknown')
        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)

        # Determine winner and apply color
        if away_score > home_score:
            away_color = Colors.BRIGHT_GREEN
            home_color = Colors.RESET
            winner_marker = "✓"
        else:
            away_color = Colors.RESET
            home_color = Colors.BRIGHT_GREEN
            winner_marker = "✓"

        print(f"  Game {idx}:")
        print(f"    {away_color}{away_team:25s} {away_score:2d}{Colors.RESET} {'  ' + winner_marker if away_score > home_score else ''}")
        print(f"    {home_color}{home_team:25s} {home_score:2d}{Colors.RESET} {'  ' + winner_marker if home_score > away_score else ''}")
        print()

    print(f"{Colors.GREEN}{'═' * 40}{Colors.RESET}\n")


def display_weekly_summary(result: Dict[str, Any]) -> None:
    """
    Format and display summary of a week's worth of games.

    Args:
        result: Dictionary containing week simulation results with keys:
            - games_played: Total games in the week
            - week_number: Week number
            - game_results: List of all game results
            - standings_update: Updated standings information

    Displays:
        - Week number and total games
        - Condensed game results (scores only)
        - Division leader updates
        - Notable performances
    """
    if not result:
        print(f"{Colors.RED}No weekly results available{Colors.RESET}")
        return

    week_number = result.get('week_number', '?')
    games_played = result.get('games_played', 0)
    game_results = result.get('game_results', [])

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_BLUE}═══ WEEK {week_number} SUMMARY ═══{Colors.RESET}")
    print(f"🏈 Total Games: {Colors.BOLD}{games_played}{Colors.RESET}\n")

    # Display condensed game results in a compact format
    for idx, game in enumerate(game_results, 1):
        away_team = game.get('away_team', 'UNK')[:20]
        home_team = game.get('home_team', 'UNK')[:20]
        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)

        # Format: Away @ Home: Score
        result_str = f"{away_team:20s} @ {home_team:20s} : {away_score:2d}-{home_score:2d}"

        # Highlight winner
        if away_score > home_score:
            print(f"  {Colors.BRIGHT_GREEN}{result_str}{Colors.RESET}")
        else:
            print(f"  {result_str}")

    print(f"\n{Colors.BRIGHT_BLUE}{'═' * 60}{Colors.RESET}\n")


def display_standings(standings_data: Dict[str, Any]) -> None:
    """
    Format and display division standings tables.

    Args:
        standings_data: Dictionary containing standings organized by division:
            - division_name: List of team standings with record, points, etc.

    Displays:
        - All 8 NFL divisions (AFC and NFC)
        - Team records (W-L-T format)
        - Win percentage
        - Points for/against
        - Division ranking

    Example output:
        ═══ AFC EAST ═══
        1. Buffalo Bills          10-3-0  .769  PF:324  PA:256
        2. Miami Dolphins          8-5-0  .615  PF:298  PA:278
    """
    if not standings_data:
        print(f"{Colors.RED}No standings data available{Colors.RESET}")
        return

    # Extract divisions dict from standings_data structure
    # get_standings() returns {'divisions': {...}, 'conferences': {...}, ...}
    divisions_data = standings_data.get('divisions', {})

    if not divisions_data:
        print(f"{Colors.RED}No division standings available{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}═══ NFL STANDINGS ═══{Colors.RESET}\n")

    # Display AFC divisions
    print(f"{Colors.BOLD}{Colors.BLUE}═══ AFC ═══{Colors.RESET}")
    _display_conference_standings(divisions_data, 'AFC')

    print()

    # Display NFC divisions
    print(f"{Colors.BOLD}{Colors.GREEN}═══ NFC ═══{Colors.RESET}")
    _display_conference_standings(divisions_data, 'NFC')

    print(f"\n{Colors.BRIGHT_CYAN}{'═' * 80}{Colors.RESET}\n")


def _display_conference_standings(standings_data: Dict[str, Any], conference: str) -> None:
    """
    Helper function to display standings for a single conference.

    Args:
        standings_data: Complete standings data dictionary
        conference: 'AFC' or 'NFC'
    """
    divisions = ['East', 'North', 'South', 'West']

    for division in divisions:
        division_key = f"{conference} {division}"
        teams = standings_data.get(division_key, [])

        if not teams:
            continue

        print(f"\n  {Colors.BOLD}{division_key}{Colors.RESET}")
        print(f"  {Colors.DIM}{'─' * 70}{Colors.RESET}")

        for rank, team in enumerate(teams, 1):
            # Extract data from team['standing'] object
            team_id = team.get('team_id')
            standing = team.get('standing')

            if not standing:
                continue

            # Get team name from team_id
            from team_management.teams.team_loader import get_team_by_id
            try:
                team_info = get_team_by_id(team_id)
                team_name = str(team_info)[:22]  # Team object's __str__ returns team name
            except:
                team_name = f"Team {team_id}"[:22]

            # Extract stats from standing object
            wins = standing.wins
            losses = standing.losses
            ties = standing.ties
            win_pct = standing.win_percentage
            points_for = standing.points_for
            points_against = standing.points_against

            # Format record string
            if ties > 0:
                record = f"{wins:2d}-{losses:2d}-{ties:1d}"
            else:
                record = f"{wins:2d}-{losses:2d}   "

            # Color code by division place
            if rank == 1:
                rank_color = Colors.BRIGHT_GREEN
            elif rank == 2:
                rank_color = Colors.BRIGHT_YELLOW
            else:
                rank_color = Colors.RESET

            print(f"  {rank_color}{rank}. {team_name:22s}  {record}  {win_pct:.3f}  "
                  f"PF:{points_for:3d}  PA:{points_against:3d}{Colors.RESET}")


def display_upcoming_games(games: List[Dict[str, Any]], days: int = 7) -> None:
    """
    Show next N days of scheduled games.

    Args:
        games: List of upcoming game dictionaries with keys:
            - date: Game date
            - away_team: Away team name/ID
            - home_team: Home team name/ID
            - week: Week number
        days: Number of days to look ahead (default: 7)

    Displays:
        - Date and week for each game
        - Matchup details (Away @ Home)
        - Total games in the upcoming period
    """
    if not games:
        print(f"{Colors.YELLOW}No games scheduled in the next {days} days{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}═══ UPCOMING GAMES (Next {days} Days) ═══{Colors.RESET}\n")

    # Group games by date
    games_by_date: Dict[str, List[Dict[str, Any]]] = {}
    for game in games:
        game_date = str(game.get('date', 'Unknown'))
        if game_date not in games_by_date:
            games_by_date[game_date] = []
        games_by_date[game_date].append(game)

    # Display games grouped by date
    for game_date in sorted(games_by_date.keys()):
        date_games = games_by_date[game_date]
        week = date_games[0].get('week', '?') if date_games else '?'

        print(f"{Colors.BOLD}{Colors.CYAN}📅 {game_date} (Week {week}){Colors.RESET}")

        for game in date_games:
            away_team = game.get('away_team', 'Unknown')[:25]
            home_team = game.get('home_team', 'Unknown')[:25]

            print(f"   🏈 {away_team:25s} @ {home_team:25s}")

        print()

    total_games = len(games)
    print(f"{Colors.BRIGHT_MAGENTA}Total: {total_games} game{'s' if total_games != 1 else ''}{Colors.RESET}")
    print(f"{Colors.BRIGHT_MAGENTA}{'═' * 60}{Colors.RESET}\n")


def display_season_summary(result: Dict[str, Any]) -> None:
    """
    Display final season statistics and playoff information.

    Args:
        result: Dictionary containing season summary data:
            - total_games: Total games simulated
            - season_year: Season year
            - playoff_teams: List of playoff qualifiers
            - division_winners: List of division champions
            - final_standings: Complete final standings

    Displays:
        - Total games played
        - Playoff bracket/seeding
        - Division champions
        - Wild card teams
        - Notable season statistics
    """
    if not result:
        print(f"{Colors.RED}No season summary available{Colors.RESET}")
        return

    season_year = result.get('season_year', 'Unknown')
    total_games = result.get('total_games', 0)

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════╗")
    print(f"║                                           ║")
    print(f"║       {season_year} SEASON COMPLETE              ║")
    print(f"║                                           ║")
    print(f"╚═══════════════════════════════════════════╝{Colors.RESET}\n")

    print(f"{Colors.BOLD}Season Statistics:{Colors.RESET}")
    print(f"  🏈 Total Games Played: {Colors.BRIGHT_GREEN}{total_games}{Colors.RESET}")

    # Display playoff teams if available
    playoff_teams = result.get('playoff_teams', {})
    if playoff_teams:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}🏆 PLAYOFF TEAMS 🏆{Colors.RESET}\n")

        for conference in ['AFC', 'NFC']:
            conf_teams = playoff_teams.get(conference, {})
            if conf_teams:
                print(f"{Colors.BOLD}{conference}:{Colors.RESET}")
                for seed in range(1, 8):
                    seed_key = f"{seed}_seed"
                    team = conf_teams.get(seed_key)
                    if team:
                        team_name = team.get('name', 'Unknown')
                        record = team.get('record', '0-0')
                        emoji = "👑" if seed <= 4 else "🎫"
                        print(f"  {emoji} #{seed} - {team_name:25s} ({record})")
                print()

    # Display division winners
    division_winners = result.get('division_winners', {})
    if division_winners:
        print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}Division Champions:{Colors.RESET}")
        for division, winner in division_winners.items():
            winner_name = winner.get('name', 'Unknown') if isinstance(winner, dict) else winner
            print(f"  🏆 {division:20s} - {winner_name}")

    print(f"\n{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}\n")
    print(f"{Colors.BOLD}{Colors.GREEN}Season simulation complete! Playoff bracket ready.{Colors.RESET}\n")


def progress_bar(current: int, total: int, width: int = 50,
                 label: str = "Progress") -> str:
    """
    Generate ASCII progress bar for terminal display.

    Args:
        current: Current progress value
        total: Total/maximum value
        width: Width of the progress bar in characters (default: 50)
        label: Label to display before the progress bar (default: "Progress")

    Returns:
        Formatted progress bar string with percentage

    Example output:
        Progress: [████████████████████░░░░░░░░░░] 65.4% (112/171)
    """
    if total == 0:
        percentage = 0.0
    else:
        percentage = (current / total) * 100

    # Calculate filled portion
    filled_width = int((current / total) * width) if total > 0 else 0

    # Build progress bar
    filled = '█' * filled_width
    empty = '░' * (width - filled_width)

    # Color based on completion
    if percentage >= 100:
        color = Colors.BRIGHT_GREEN
    elif percentage >= 75:
        color = Colors.GREEN
    elif percentage >= 50:
        color = Colors.YELLOW
    elif percentage >= 25:
        color = Colors.BRIGHT_YELLOW
    else:
        color = Colors.RED

    # Format output
    bar = f"{color}{label}: [{filled}{empty}] {percentage:5.1f}% ({current}/{total}){Colors.RESET}"

    return bar


def clear_screen() -> None:
    """
    Clear the terminal screen (cross-platform).

    Works on Unix/Linux/macOS and Windows systems.
    """
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def print_separator(char: str = '═', length: int = 80, color: str = Colors.CYAN) -> None:
    """
    Print a horizontal separator line.

    Args:
        char: Character to use for the separator (default: '═')
        length: Length of the separator line (default: 80)
        color: ANSI color code to use (default: Colors.CYAN)
    """
    print(f"{color}{char * length}{Colors.RESET}")


def print_error(message: str) -> None:
    """
    Print an error message with formatting.

    Args:
        message: Error message to display
    """
    print(f"\n{Colors.BOLD}{Colors.RED}❌ ERROR: {message}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """
    Print a success message with formatting.

    Args:
        message: Success message to display
    """
    print(f"\n{Colors.BOLD}{Colors.GREEN}✓ SUCCESS: {message}{Colors.RESET}\n")


def print_warning(message: str) -> None:
    """
    Print a warning message with formatting.

    Args:
        message: Warning message to display
    """
    print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠️  WARNING: {message}{Colors.RESET}\n")


def print_info(message: str) -> None:
    """
    Print an informational message with formatting.

    Args:
        message: Info message to display
    """
    print(f"\n{Colors.BOLD}{Colors.CYAN}ℹ️  INFO: {message}{Colors.RESET}\n")


def format_team_name(team_id: int, teams_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Format team name from team ID.

    Args:
        team_id: Numerical team ID (1-32)
        teams_data: Optional team data dictionary for lookups

    Returns:
        Formatted team name or placeholder if not found
    """
    if teams_data and str(team_id) in teams_data:
        team = teams_data[str(team_id)]
        return team.get('full_name', f'Team {team_id}')
    else:
        return f'Team {team_id}'


def format_record(wins: int, losses: int, ties: int = 0) -> str:
    """
    Format team record as a string.

    Args:
        wins: Number of wins
        losses: Number of losses
        ties: Number of ties (default: 0)

    Returns:
        Formatted record string (e.g., "10-6" or "10-6-1")
    """
    if ties > 0:
        return f"{wins}-{losses}-{ties}"
    return f"{wins}-{losses}"


def format_date(date_obj: Any) -> str:
    """
    Format date object for display.

    Args:
        date_obj: Date object (Date, date, or string)

    Returns:
        Formatted date string (e.g., "2024-09-05")
    """
    if isinstance(date_obj, str):
        return date_obj

    try:
        return str(date_obj)
    except Exception:
        return "Unknown Date"


# Example usage and testing
if __name__ == "__main__":
    print_banner()

    # Mock controller for demonstration
    class MockController:
        class MockCalendar:
            def get_current_date(self):
                return "2024-09-05"

            def get_current_phase(self):
                class Phase:
                    value = "Regular Season"
                return Phase()

            def get_current_week(self):
                return 1

        def __init__(self):
            self.calendar = self.MockCalendar()
            self.games_played = 0

    controller = MockController()
    print_status(controller)
    print_menu()

    # Test progress bar
    print("\nProgress Bar Examples:")
    print(progress_bar(0, 100, label="Week 1"))
    print(progress_bar(25, 100, label="Week 5"))
    print(progress_bar(50, 100, label="Week 9"))
    print(progress_bar(75, 100, label="Week 13"))
    print(progress_bar(100, 100, label="Week 18"))

    # Test message functions
    print_success("Season initialized successfully!")
    print_info("Simulating games...")
    print_warning("Low disk space detected")
    print_error("Failed to load standings")

    print_separator()
    print(f"\n{Colors.BOLD}Display utilities loaded successfully!{Colors.RESET}\n")
