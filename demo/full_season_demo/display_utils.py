"""
Terminal Display Utilities for Full Season Simulator

Unified display functions for complete NFL season simulation including
regular season, playoffs, and offseason phases. Merges capabilities from
both interactive_season_sim and interactive_playoff_sim demos.

Provides:
- Phase-aware menus and status displays
- Regular season standings and game results
- Playoff bracket and seeding visualization
- Season summary and championship displays
- Consistent terminal formatting across all phases
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
    Display ASCII art banner for the full season simulator.

    Shows the application title with styled formatting for visual appeal.
    """
    banner = f"""
{Colors.BOLD}{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              NFL FULL SEASON SIMULATOR                           ║
║                                                                  ║
║              The Owner's Sim - Complete Season Edition           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def display_status(controller: Any) -> None:
    """
    Show current simulation status based on active phase.

    Args:
        controller: FullSeasonController with current state

    Displays:
        - Current date and phase
        - Phase-specific information (week, round, etc.)
        - Total games played
        - Phase progression indicators
    """
    try:
        state = controller.get_current_state()
        current_phase = state.get('current_phase', 'unknown')
        current_date = state.get('current_date', 'Unknown')
        total_games = state.get('total_games_played', 0)

        print(f"\n{Colors.BOLD}{Colors.CYAN}═══ SIMULATION STATUS ═══{Colors.RESET}")
        print(f"📅 Date: {Colors.BOLD}{current_date}{Colors.RESET}")
        print(f"⚡ Phase: {Colors.BOLD}{Colors.YELLOW}{current_phase.upper().replace('_', ' ')}{Colors.RESET}")
        print(f"🏈 Total Games: {Colors.BOLD}{total_games}{Colors.RESET}")

        # Phase-specific details
        if current_phase == 'regular_season':
            week = state.get('current_week', 1)
            print(f"📊 Week: {Colors.BOLD}Week {week}{Colors.RESET}")
            print(f"📈 Progress: {total_games}/272 games")
        elif current_phase == 'playoffs':
            round_name = state.get('current_round', 'unknown')
            round_display = _get_round_display_name(round_name)
            print(f"🏆 Round: {Colors.BOLD}{round_display}{Colors.RESET}")
            print(f"📈 Progress: {total_games - 272}/13 playoff games")
        elif current_phase == 'offseason':
            print(f"{Colors.BRIGHT_GREEN}Season Complete!{Colors.RESET}")

        print(f"{Colors.CYAN}{'═' * 40}{Colors.RESET}\n")

    except Exception as e:
        print(f"{Colors.RED}Error displaying status: {e}{Colors.RESET}")


def display_main_menu(current_phase: str, week: int = 0, round_name: str = '') -> None:
    """
    Display phase-aware interactive command menu.

    Args:
        current_phase: Current season phase ('regular_season', 'playoffs', 'offseason')
        week: Current week number (for regular season)
        round_name: Current playoff round (for playoffs)

    Displays appropriate menu options based on current phase.
    """
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_YELLOW}╔═══ COMMAND MENU ═══╗{Colors.RESET}")

    if current_phase == 'regular_season':
        print(f"{Colors.YELLOW}║{Colors.RESET}  1️⃣  Simulate 1 Day")
        print(f"{Colors.YELLOW}║{Colors.RESET}  2️⃣  Simulate 1 Week")
        print(f"{Colors.YELLOW}║{Colors.RESET}  3️⃣  Simulate to Playoffs")
        print(f"{Colors.YELLOW}║{Colors.RESET}  4️⃣  View Standings")
        print(f"{Colors.YELLOW}║{Colors.RESET}  5️⃣  View Upcoming Games")
        print(f"{Colors.YELLOW}║{Colors.RESET}  6️⃣  View Season Summary")

        # Playoff picture option (week 10+)
        if week >= 10:
            print(f"{Colors.YELLOW}║{Colors.RESET}  {Colors.BRIGHT_GREEN}7️⃣  View Playoff Picture{Colors.RESET}")

    elif current_phase == 'playoffs':
        round_display = _get_round_display_name(round_name)
        print(f"{Colors.YELLOW}║{Colors.RESET}  Current: {Colors.BOLD}{round_display}{Colors.RESET}")
        print(f"{Colors.YELLOW}║{Colors.RESET}")
        print(f"{Colors.YELLOW}║{Colors.RESET}  1️⃣  Advance 1 Day")
        print(f"{Colors.YELLOW}║{Colors.RESET}  2️⃣  Advance 7 Days")
        print(f"{Colors.YELLOW}║{Colors.RESET}  3️⃣  Complete Current Round")
        print(f"{Colors.YELLOW}║{Colors.RESET}  4️⃣  View Playoff Bracket")
        print(f"{Colors.YELLOW}║{Colors.RESET}  5️⃣  View Completed Games")
        print(f"{Colors.YELLOW}║{Colors.RESET}  {Colors.BRIGHT_GREEN}6️⃣  Simulate to Super Bowl{Colors.RESET}")

    elif current_phase == 'offseason':
        print(f"{Colors.YELLOW}║{Colors.RESET}  {Colors.BRIGHT_CYAN}Season Complete!{Colors.RESET}")
        print(f"{Colors.YELLOW}║{Colors.RESET}")
        print(f"{Colors.YELLOW}║{Colors.RESET}  1️⃣  View Final Standings")
        print(f"{Colors.YELLOW}║{Colors.RESET}  2️⃣  View Playoff Results")
        print(f"{Colors.YELLOW}║{Colors.RESET}  3️⃣  View Season Summary")
        print(f"{Colors.YELLOW}║{Colors.RESET}  4️⃣  View Super Bowl Champion")

    print(f"{Colors.YELLOW}║{Colors.RESET}  0️⃣  Exit")
    print(f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}╚════════════════════╝{Colors.RESET}\n")


def display_phase_transition(from_phase: str, to_phase: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Display notification when transitioning between phases.

    Args:
        from_phase: Previous phase name
        to_phase: New phase name
        details: Optional transition details (seeding, dates, etc.)

    Shows:
        - Clear phase change notification
        - Relevant transition information
        - Next steps guidance
    """
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{'═' * 80}{Colors.RESET}")

    if to_phase == 'playoffs':
        print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}🏆 REGULAR SEASON COMPLETE - PLAYOFFS STARTING 🏆{Colors.RESET}".center(90))
        print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{'═' * 80}{Colors.RESET}")

        if details:
            wild_card_date = details.get('wild_card_date', 'TBD')
            print(f"\n{Colors.BOLD}Playoff Information:{Colors.RESET}")
            print(f"  📅 Wild Card Weekend: {Colors.BRIGHT_CYAN}{wild_card_date}{Colors.RESET}")
            print(f"  🎯 Playoff Seeding: {Colors.BRIGHT_GREEN}Calculated from Final Standings{Colors.RESET}")
            print(f"  🏈 Total Playoff Games: {Colors.BOLD}13{Colors.RESET}")

    elif to_phase == 'offseason':
        print(f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}🏆 SUPER BOWL COMPLETE - SEASON FINISHED 🏆{Colors.RESET}".center(90))
        print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{'═' * 80}{Colors.RESET}")

        if details:
            champion = details.get('champion', 'Unknown')
            print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}Super Bowl Champion: {champion}{Colors.RESET}")

    print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{'═' * 80}{Colors.RESET}\n")
    print(f"{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
    input()


def display_standings(standings_data: Dict[str, Any]) -> None:
    """
    Format and display division standings tables.

    Args:
        standings_data: Dictionary containing standings organized by division

    Displays:
        - All 8 NFL divisions (AFC and NFC)
        - Team records (W-L-T format)
        - Win percentage
        - Points for/against
        - Division ranking
    """
    if not standings_data:
        print(f"{Colors.RED}No standings data available{Colors.RESET}")
        return

    # Extract divisions dict from standings_data structure
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
                team_name = str(team_info)[:22]
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


def display_playoff_bracket(bracket: Any, seeding: Any) -> None:
    """
    Display current playoff bracket with teams and seeds.

    Args:
        bracket: PlayoffBracket object containing playoff games
        seeding: PlayoffSeeding object with team seeding information

    Displays:
        - Visual playoff bracket structure
        - Team names with seeds
        - Round organization
        - Conference separation
    """
    from team_management.teams.team_loader import get_team_by_id

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════════════════════╗")
    print(f"║                                                           ║")
    print(f"║              {seeding.season} NFL PLAYOFF BRACKET                    ║")
    print(f"║                                                           ║")
    print(f"╚═══════════════════════════════════════════════════════════╝{Colors.RESET}\n")

    round_display_name = _get_round_display_name(bracket.round_name)
    print(f"{Colors.BOLD}{Colors.YELLOW}Current Round: {round_display_name}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}\n")

    # Get AFC and NFC games
    afc_games = bracket.get_afc_games()
    nfc_games = bracket.get_nfc_games()

    # Display AFC bracket
    if afc_games:
        print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}                         AFC                              {Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.RESET}\n")

        for game in afc_games:
            _display_bracket_game(game, seeding, get_team_by_id)
        print()

    # Display NFC bracket
    if nfc_games:
        print(f"{Colors.BOLD}{Colors.GREEN}{'═' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}                         NFC                              {Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'═' * 60}{Colors.RESET}\n")

        for game in nfc_games:
            _display_bracket_game(game, seeding, get_team_by_id)
        print()

    # Display Super Bowl if applicable
    if bracket.is_super_bowl():
        sb_game = bracket.get_super_bowl_game()
        if sb_game:
            print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{'═' * 60}{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}                    SUPER BOWL                            {Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{'═' * 60}{Colors.RESET}\n")
            _display_bracket_game(sb_game, seeding, get_team_by_id)
            print()

    print(f"{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}\n")


def _display_bracket_game(game: Any, seeding: Any, get_team_func: Any) -> None:
    """Helper function to display a single bracket game."""
    try:
        away_team = str(get_team_func(game.away_team_id))[:25]
    except:
        away_team = f"Team {game.away_team_id}"[:25]

    try:
        home_team = str(get_team_func(game.home_team_id))[:25]
    except:
        home_team = f"Team {game.home_team_id}"[:25]

    away_seed_obj = seeding.get_seed(game.away_team_id)
    home_seed_obj = seeding.get_seed(game.home_team_id)
    away_record = away_seed_obj.record_string if away_seed_obj else "?"
    home_record = home_seed_obj.record_string if home_seed_obj else "?"

    print(f"  {Colors.BOLD}Game {game.game_number}:{Colors.RESET} {Colors.DIM}{game.game_date}{Colors.RESET}")
    print(f"    {Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team:25s} {Colors.DIM}({away_record}){Colors.RESET}")
    print(f"       {Colors.BOLD}@{Colors.RESET}")
    print(f"    {Colors.CYAN}({game.home_seed}){Colors.RESET} {home_team:25s} {Colors.DIM}({home_record}){Colors.RESET}")
    print()


def display_season_summary(summary: Dict[str, Any]) -> None:
    """
    Display comprehensive season summary.

    Args:
        summary: Dictionary containing complete season statistics

    Displays:
        - Regular season results
        - Playoff results
        - Super Bowl champion
        - Statistical leaders
        - Season milestones
    """
    if not summary:
        print(f"{Colors.RED}No season summary available{Colors.RESET}")
        return

    season_year = summary.get('season_year', 'Unknown')
    total_games = summary.get('total_games', 0)
    champion_id = summary.get('super_bowl_champion')

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════╗")
    print(f"║                                           ║")
    print(f"║       {season_year} SEASON SUMMARY                ║")
    print(f"║                                           ║")
    print(f"╚═══════════════════════════════════════════╝{Colors.RESET}\n")

    print(f"{Colors.BOLD}Season Statistics:{Colors.RESET}")
    print(f"  🏈 Total Games: {Colors.BRIGHT_GREEN}{total_games}{Colors.RESET}")
    print(f"  📊 Regular Season: {Colors.BOLD}272 games{Colors.RESET}")
    print(f"  🏆 Playoffs: {Colors.BOLD}13 games{Colors.RESET}")

    # Super Bowl Champion
    if champion_id:
        from team_management.teams.team_loader import get_team_by_id
        try:
            champion = get_team_by_id(champion_id)
            champion_name = str(champion)
        except:
            champion_name = f"Team {champion_id}"

        print(f"\n{Colors.BOLD}{Colors.BRIGHT_YELLOW}🏆 SUPER BOWL CHAMPION 🏆{Colors.RESET}")
        print(f"  {Colors.BRIGHT_GREEN}{champion_name}{Colors.RESET}")

    # Stat leaders if available
    regular_leaders = summary.get('regular_season_leaders', {})
    playoff_leaders = summary.get('playoff_leaders', {})

    if regular_leaders:
        print(f"\n{Colors.BOLD}Regular Season Leaders:{Colors.RESET}")
        _display_stat_leaders(regular_leaders)

    if playoff_leaders:
        print(f"\n{Colors.BOLD}Playoff Leaders:{Colors.RESET}")
        _display_stat_leaders(playoff_leaders)

    print(f"\n{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}\n")


def _display_stat_leaders(leaders: Dict[str, Any]) -> None:
    """Helper function to display statistical leaders."""
    if 'passing' in leaders:
        passing_leader = leaders['passing']
        print(f"  🎯 Passing: {passing_leader.get('name', 'Unknown')} ({passing_leader.get('yards', 0)} yds)")

    if 'rushing' in leaders:
        rushing_leader = leaders['rushing']
        print(f"  🏃 Rushing: {rushing_leader.get('name', 'Unknown')} ({rushing_leader.get('yards', 0)} yds)")

    if 'receiving' in leaders:
        receiving_leader = leaders['receiving']
        print(f"  🙌 Receiving: {receiving_leader.get('name', 'Unknown')} ({receiving_leader.get('yards', 0)} yds)")


def display_game_results(results: List[Dict[str, Any]], context: str = 'daily') -> None:
    """
    Display game results with appropriate context.

    Args:
        results: List of game result dictionaries
        context: Display context ('daily', 'weekly', 'playoff')
    """
    if not results:
        print(f"{Colors.DIM}No games played{Colors.RESET}")
        return

    if context == 'playoff':
        display_playoff_game_results(results)
        return

    header = "DAILY RESULTS" if context == 'daily' else "WEEKLY RESULTS"
    print(f"\n{Colors.BOLD}{Colors.GREEN}═══ {header} ═══{Colors.RESET}\n")

    for idx, game in enumerate(results, 1):
        away_team = game.get('away_team', 'Unknown')[:25]
        home_team = game.get('home_team', 'Unknown')[:25]
        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)

        winner_is_away = away_score > home_score
        if winner_is_away:
            print(f"  {Colors.BRIGHT_GREEN}✓ {away_team:25s} {away_score:2d}{Colors.RESET} @ {home_team:25s} {home_score:2d}")
        else:
            print(f"    {away_team:25s} {away_score:2d} @ {Colors.BRIGHT_GREEN}✓ {home_team:25s} {home_score:2d}{Colors.RESET}")

    print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}\n")


def display_playoff_game_results(game_results: List[Dict[str, Any]]) -> None:
    """Display playoff game results with playoff-specific formatting."""
    from team_management.teams.team_loader import get_team_by_id

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}═══ PLAYOFF GAME RESULTS ═══{Colors.RESET}\n")

    for game in game_results:
        away_team_id = game.get('away_team_id')
        home_team_id = game.get('home_team_id')

        # Get team names
        try:
            away_team = str(get_team_by_id(away_team_id)) if away_team_id else game.get('away_team', 'Unknown')
        except:
            away_team = f"Team {away_team_id}"

        try:
            home_team = str(get_team_by_id(home_team_id)) if home_team_id else game.get('home_team', 'Unknown')
        except:
            home_team = f"Team {home_team_id}"

        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)
        away_seed = game.get('away_seed', '?')
        home_seed = game.get('home_seed', '?')
        round_name = game.get('round_name', 'unknown')

        round_display = _get_round_display_name(round_name)
        print(f"{Colors.BOLD}{round_display}{Colors.RESET}")

        winner_is_away = away_score > home_score
        if winner_is_away:
            print(f"  {Colors.BRIGHT_GREEN}✓ ({away_seed}) {away_team:30s} {away_score:2d}{Colors.RESET} WINNER")
            print(f"    ({home_seed}) {home_team:30s} {home_score:2d}")
        else:
            print(f"    ({away_seed}) {away_team:30s} {away_score:2d}")
            print(f"  {Colors.BRIGHT_GREEN}✓ ({home_seed}) {home_team:30s} {home_score:2d}{Colors.RESET} WINNER")
        print()

    print(f"{Colors.BRIGHT_GREEN}{'═' * 60}{Colors.RESET}\n")


def _get_round_display_name(round_name: str) -> str:
    """Get display name for a playoff round."""
    display_names = {
        'wild_card': 'Wild Card Round',
        'divisional': 'Divisional Round',
        'conference': 'Conference Championships',
        'super_bowl': 'Super Bowl'
    }
    return display_names.get(round_name, round_name.replace('_', ' ').title())


def progress_bar(current: int, total: int, width: int = 50, label: str = "Progress") -> str:
    """
    Generate ASCII progress bar for terminal display.

    Args:
        current: Current progress value
        total: Total/maximum value
        width: Width of the progress bar in characters
        label: Label to display before the progress bar

    Returns:
        Formatted progress bar string with percentage
    """
    if total == 0:
        percentage = 0.0
    else:
        percentage = (current / total) * 100

    filled_width = int((current / total) * width) if total > 0 else 0
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

    bar = f"{color}{label}: [{filled}{empty}] {percentage:5.1f}% ({current}/{total}){Colors.RESET}"
    return bar


def clear_screen() -> None:
    """Clear the terminal screen (cross-platform)."""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def print_separator(char: str = '═', length: int = 80, color: str = Colors.CYAN) -> None:
    """Print a horizontal separator line."""
    print(f"{color}{char * length}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message with formatting."""
    print(f"\n{Colors.BOLD}{Colors.RED}❌ ERROR: {message}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """Print a success message with formatting."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}✓ SUCCESS: {message}{Colors.RESET}\n")


def print_warning(message: str) -> None:
    """Print a warning message with formatting."""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠️  WARNING: {message}{Colors.RESET}\n")


def print_info(message: str) -> None:
    """Print an informational message with formatting."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}ℹ️  INFO: {message}{Colors.RESET}\n")


# Example usage
if __name__ == "__main__":
    print_banner()

    # Test phase transitions
    display_phase_transition(
        'regular_season',
        'playoffs',
        {'wild_card_date': '2025-01-18'}
    )

    # Test progress bars
    print("\nProgress Bar Examples:")
    print(progress_bar(136, 272, label="Regular Season"))
    print(progress_bar(7, 13, label="Playoffs"))
    print(progress_bar(285, 285, label="Full Season"))

    # Test message functions
    print_success("Phase transition completed!")
    print_info("Calculating playoff seeding...")
    print_warning("Low disk space detected")
    print_error("Failed to load standings")

    print_separator()
    print(f"\n{Colors.BOLD}Full Season display utilities loaded successfully!{Colors.RESET}\n")
