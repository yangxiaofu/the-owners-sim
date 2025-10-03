"""
Terminal Display Utilities for Interactive Playoff Simulator

Provides formatted display functions for playoff-specific visualization including
playoff brackets, game results with playoff context, round summaries, and
playoff-specific menus.
"""

from typing import Dict, List, Any, Optional
from datetime import date

# Import team loader for converting team IDs to names
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from team_management.teams.team_loader import get_team_by_id


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
    Display ASCII art banner for the interactive playoff simulator.

    Shows the application title with styled formatting for visual appeal.
    """
    banner = f"""
{Colors.BOLD}{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              NFL INTERACTIVE PLAYOFF SIMULATOR                   ║
║                                                                  ║
║              The Owner's Sim - Dynasty Edition                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def print_status(controller) -> None:
    """
    Show current playoff simulation status.

    Args:
        controller: PlayoffController object with current state

    Displays:
        - Current playoff round
        - Games completed in playoffs
        - Games remaining in playoffs
        - Current date
    """
    # Extract state from controller
    state = controller.get_current_state()
    # Use active_round if available (accurate), fall back to current_round for compatibility
    active_round = state.get('active_round', state['current_round'])
    current_round = active_round.replace('_', ' ').title()
    games_completed = state['games_played']
    total_playoff_games = 13  # Wild Card (6) + Divisional (4) + Conference (2) + Super Bowl (1)
    games_remaining = total_playoff_games - games_completed
    current_date = state['current_date']

    print(f"\n{Colors.BOLD}{Colors.CYAN}═══ PLAYOFF STATUS ═══{Colors.RESET}")
    print(f"📅 Current Date: {Colors.BOLD}{current_date}{Colors.RESET}")
    print(f"🏆 Current Round: {Colors.BOLD}{Colors.YELLOW}{current_round}{Colors.RESET}")
    print(f"✅ Games Completed: {Colors.BOLD}{games_completed}{Colors.RESET} / {total_playoff_games}")
    print(f"📋 Games Remaining: {Colors.BOLD}{games_remaining}{Colors.RESET}")
    print(f"{Colors.CYAN}{'═' * 40}{Colors.RESET}\n")


def display_playoff_bracket(bracket: Any, seeding: Any) -> None:
    """
    Display current playoff bracket with teams and seeds.

    Args:
        bracket: PlayoffBracket object containing playoff games
        seeding: PlayoffSeeding object with team seeding information

    Displays:
        - Visual playoff bracket structure
        - Team names with seeds
        - Round organization (Wild Card, Divisional, Conference, Super Bowl)
        - Conference separation (AFC/NFC)
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
    """
    Helper function to display a single bracket game.

    Args:
        game: PlayoffGame object
        seeding: PlayoffSeeding object
        get_team_func: Function to get team name from ID
    """
    # Get team names
    try:
        away_team = str(get_team_func(game.away_team_id))[:25]
    except:
        away_team = f"Team {game.away_team_id}"[:25]

    try:
        home_team = str(get_team_func(game.home_team_id))[:25]
    except:
        home_team = f"Team {game.home_team_id}"[:25]

    # Get team records from seeding
    away_seed_obj = seeding.get_seed(game.away_team_id)
    home_seed_obj = seeding.get_seed(game.home_team_id)

    away_record = away_seed_obj.record_string if away_seed_obj else "?"
    home_record = home_seed_obj.record_string if home_seed_obj else "?"

    # Format with seeds and records
    print(f"  {Colors.BOLD}Game {game.game_number}:{Colors.RESET} {Colors.DIM}{game.game_date}{Colors.RESET}")
    print(f"    {Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team:25s} {Colors.DIM}({away_record}){Colors.RESET}")
    print(f"       {Colors.BOLD}@{Colors.RESET}")
    print(f"    {Colors.CYAN}({game.home_seed}){Colors.RESET} {home_team:25s} {Colors.DIM}({home_record}){Colors.RESET}")
    print()


def display_playoff_game_results(game_results: List[Dict[str, Any]]) -> None:
    """
    Show completed playoff games with playoff context.

    Args:
        game_results: List of game result dictionaries with keys:
            - away_team: Away team name/ID
            - home_team: Home team name/ID
            - away_score: Away team score
            - home_score: Home team score
            - away_seed: Away team playoff seed
            - home_seed: Home team playoff seed
            - round_name: Playoff round
            - conference: AFC/NFC/None

    Displays:
        - Final scores with winner highlighted
        - Playoff seeds for context
        - Round information
        - Advancing team indicators
    """
    if not game_results:
        print(f"{Colors.YELLOW}No playoff games completed yet{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}═══ PLAYOFF GAME RESULTS ═══{Colors.RESET}\n")

    for idx, game in enumerate(game_results, 1):
        # Get team IDs and convert to team names
        away_team_id = game.get('away_team_id')
        home_team_id = game.get('home_team_id')

        # Get team names from team loader
        if away_team_id is not None:
            try:
                away_team_obj = get_team_by_id(away_team_id)
                away_team = away_team_obj.full_name if away_team_obj else f"Team {away_team_id}"
            except Exception as e:
                away_team = f"Team {away_team_id}"
        else:
            away_team = game.get('away_team', 'Unknown')

        if home_team_id is not None:
            try:
                home_team_obj = get_team_by_id(home_team_id)
                home_team = home_team_obj.full_name if home_team_obj else f"Team {home_team_id}"
            except Exception as e:
                home_team = f"Team {home_team_id}"
        else:
            home_team = game.get('home_team', 'Unknown')

        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)
        away_seed = game.get('away_seed', '?')
        home_seed = game.get('home_seed', '?')
        round_name = game.get('round_name', 'unknown')
        conference = game.get('conference', '')

        # Determine winner
        winner_is_away = away_score > home_score

        # Get round display name
        round_display = _get_round_display_name(round_name)

        # Conference label
        conf_label = f"{conference} " if conference else ""

        print(f"{Colors.BOLD}{conf_label}{round_display}{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")

        # Display away team
        if winner_is_away:
            print(f"  {Colors.BRIGHT_GREEN}✓ ({away_seed}) {away_team:30s} {away_score:2d}{Colors.RESET} {Colors.BOLD}WINNER{Colors.RESET}")
            print(f"    ({home_seed}) {home_team:30s} {home_score:2d}")
        else:
            print(f"    ({away_seed}) {away_team:30s} {away_score:2d}")
            print(f"  {Colors.BRIGHT_GREEN}✓ ({home_seed}) {home_team:30s} {home_score:2d}{Colors.RESET} {Colors.BOLD}WINNER{Colors.RESET}")

        print()

    print(f"{Colors.BRIGHT_GREEN}{'═' * 60}{Colors.RESET}\n")


def display_round_summary(round_name: str, games: List[Dict[str, Any]]) -> None:
    """
    Summary of a complete playoff round.

    Args:
        round_name: Name of the round (e.g., 'wild_card', 'divisional')
        games: List of game result dictionaries

    Displays:
        - Round name and status
        - All matchups in the round
        - Final scores
        - Teams advancing to next round
    """
    if not games:
        print(f"{Colors.RED}No games available for this round{Colors.RESET}")
        return

    round_display = _get_round_display_name(round_name)

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_BLUE}╔═══════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}║                                                           ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}║          {round_display:^45s}║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}║                  ROUND SUMMARY                            ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}║                                                           ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}╚═══════════════════════════════════════════════════════════╝{Colors.RESET}\n")

    print(f"{Colors.BOLD}Total Games: {len(games)}{Colors.RESET}\n")

    # Group by conference
    afc_games = [g for g in games if g.get('conference') == 'AFC']
    nfc_games = [g for g in games if g.get('conference') == 'NFC']
    neutral_games = [g for g in games if not g.get('conference')]

    # Display AFC games
    if afc_games:
        print(f"{Colors.BOLD}{Colors.BLUE}AFC Games:{Colors.RESET}")
        for game in afc_games:
            _display_round_game(game)
        print()

    # Display NFC games
    if nfc_games:
        print(f"{Colors.BOLD}{Colors.GREEN}NFC Games:{Colors.RESET}")
        for game in nfc_games:
            _display_round_game(game)
        print()

    # Display neutral/Super Bowl games
    if neutral_games:
        print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}Championship:{Colors.RESET}")
        for game in neutral_games:
            _display_round_game(game)
        print()

    # List advancing teams
    winners = []
    for game in games:
        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)

        # Get team IDs and convert to names
        if away_score > home_score:
            winner_id = game.get('away_team_id')
            if winner_id:
                try:
                    winner_obj = get_team_by_id(winner_id)
                    winner = winner_obj.full_name if winner_obj else f"Team {winner_id}"
                except:
                    winner = f"Team {winner_id}"
            else:
                winner = game.get('away_team', 'Unknown')
            seed = game.get('away_seed', '?')
        else:
            winner_id = game.get('home_team_id')
            if winner_id:
                try:
                    winner_obj = get_team_by_id(winner_id)
                    winner = winner_obj.full_name if winner_obj else f"Team {winner_id}"
                except:
                    winner = f"Team {winner_id}"
            else:
                winner = game.get('home_team', 'Unknown')
            seed = game.get('home_seed', '?')
        winners.append((seed, winner))

    if winners and round_name != 'super_bowl':
        print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}Teams Advancing:{Colors.RESET}")
        for seed, team in winners:
            print(f"  ✓ ({seed}) {team}")
        print()

    print(f"{Colors.BRIGHT_BLUE}{'═' * 60}{Colors.RESET}\n")


def _display_round_game(game: Dict[str, Any]) -> None:
    """
    Helper function to display a single game in round summary.

    Args:
        game: Game result dictionary
    """
    # Get team IDs and convert to names
    away_team_id = game.get('away_team_id')
    home_team_id = game.get('home_team_id')

    if away_team_id:
        try:
            away_team_obj = get_team_by_id(away_team_id)
            away_team = away_team_obj.full_name[:30] if away_team_obj else f"Team {away_team_id}"[:30]
        except:
            away_team = f"Team {away_team_id}"[:30]
    else:
        away_team = game.get('away_team', 'Unknown')[:30]

    if home_team_id:
        try:
            home_team_obj = get_team_by_id(home_team_id)
            home_team = home_team_obj.full_name[:30] if home_team_obj else f"Team {home_team_id}"[:30]
        except:
            home_team = f"Team {home_team_id}"[:30]
    else:
        home_team = game.get('home_team', 'Unknown')[:30]

    away_score = game.get('away_score', 0)
    home_score = game.get('home_score', 0)
    away_seed = game.get('away_seed', '?')
    home_seed = game.get('home_seed', '?')

    # Determine winner
    winner_is_away = away_score > home_score

    # Build result string with winner highlighted
    if winner_is_away:
        result = f"  {Colors.BRIGHT_GREEN}({away_seed}) {away_team:30s} {away_score:2d}{Colors.RESET} def. ({home_seed}) {home_team:30s} {home_score:2d}"
    else:
        result = f"  {Colors.BRIGHT_GREEN}({home_seed}) {home_team:30s} {home_score:2d}{Colors.RESET} def. ({away_seed}) {away_team:30s} {away_score:2d}"

    print(result)


def display_playoff_menu(current_round: str) -> None:
    """
    Display interactive command menu for playoff simulation.

    Shows all available commands specific to playoff progression:
    - 1: Simulate current round
    - 2: Simulate one game
    - 3: View bracket
    - 4: View completed games
    - 5: View round summary
    - 6: Simulate to Super Bowl
    - 0: Exit

    Args:
        current_round: Current playoff round name for context
    """
    round_display = _get_round_display_name(current_round)

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_YELLOW}╔═══ PLAYOFF COMMAND MENU ═══╗{Colors.RESET}")
    print(f"{Colors.YELLOW}║{Colors.RESET}  Current: {Colors.BOLD}{round_display}{Colors.RESET}")
    print(f"{Colors.YELLOW}║{Colors.RESET}")
    print(f"{Colors.YELLOW}║{Colors.RESET}  1️⃣  Advance 1 Day")
    print(f"{Colors.YELLOW}║{Colors.RESET}  2️⃣  Advance 7 Days (1 Week)")
    print(f"{Colors.YELLOW}║{Colors.RESET}  3️⃣  Complete Current Round ONLY")
    print(f"{Colors.YELLOW}║{Colors.RESET}  4️⃣  Show Current Bracket")
    print(f"{Colors.YELLOW}║{Colors.RESET}  5️⃣  Show Completed Games")
    print(f"{Colors.YELLOW}║{Colors.RESET}  {Colors.BRIGHT_GREEN}6️⃣  Simulate to Super Bowl{Colors.RESET}")
    print(f"{Colors.YELLOW}║{Colors.RESET}  0️⃣  Exit")
    print(f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}╚════════════════════════════╝{Colors.RESET}\n")


def _get_round_display_name(round_name: str) -> str:
    """
    Get display name for a playoff round.

    Args:
        round_name: Internal round name (e.g., 'wild_card')

    Returns:
        Display name (e.g., 'Wild Card Round')
    """
    display_names = {
        'wild_card': 'Wild Card Round',
        'divisional': 'Divisional Round',
        'conference': 'Conference Championships',
        'super_bowl': 'Super Bowl'
    }
    return display_names.get(round_name, round_name.replace('_', ' ').title())


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
        Playoffs: [████████████████████░░░░░░░░░░] 65.4% (7/11)
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


def display_super_bowl_result(game_result: Dict[str, Any]) -> None:
    """
    Display Super Bowl result with special formatting.

    Args:
        game_result: Super Bowl game result dictionary

    Displays:
        - Super Bowl banner
        - Final score with champion highlighted
        - Trophy ceremony message
    """
    away_team = game_result.get('away_team', 'Unknown')
    home_team = game_result.get('home_team', 'Unknown')
    away_score = game_result.get('away_score', 0)
    home_score = game_result.get('home_score', 0)
    season = game_result.get('season', '????')

    # Determine champion
    if away_score > home_score:
        champion = away_team
        champion_score = away_score
        runner_up = home_team
        runner_up_score = home_score
    else:
        champion = home_team
        champion_score = home_score
        runner_up = away_team
        runner_up_score = away_score

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}╔═══════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}║                                                           ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}║                    SUPER BOWL {season}                        ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}║                      CHAMPIONS                            ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}║                                                           ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}╚═══════════════════════════════════════════════════════════╝{Colors.RESET}\n")

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_YELLOW}🏆 {champion} 🏆{Colors.RESET}\n")
    print(f"{Colors.BOLD}Final Score:{Colors.RESET}")
    print(f"  {Colors.BRIGHT_GREEN}{champion:30s} {champion_score:2d}{Colors.RESET}")
    print(f"  {runner_up:30s} {runner_up_score:2d}")
    print()
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}SUPER BOWL CHAMPIONS!{Colors.RESET}")
    print(f"{Colors.DIM}The {champion} have won the Lombardi Trophy!{Colors.RESET}\n")
    print(f"{Colors.BRIGHT_MAGENTA}{'═' * 60}{Colors.RESET}\n")


def display_playoff_seeding(seeding_data: Any) -> None:
    """
    Display playoff seeding for both conferences.

    Args:
        seeding_data: PlayoffSeeding object with AFC/NFC seeding

    Displays:
        - Division winners (seeds 1-4)
        - Wild card teams (seeds 5-7)
        - Team records and positions
    """
    from team_management.teams.team_loader import get_team_by_id

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════════════════════╗")
    print(f"║                                                           ║")
    print(f"║              {seeding_data.season} NFL PLAYOFF SEEDING                   ║")
    print(f"║                                                           ║")
    print(f"╚═══════════════════════════════════════════════════════════╝{Colors.RESET}\n")

    # Display AFC seeding
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}                         AFC                              {Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.RESET}\n")

    _display_conference_seeding(seeding_data.afc, get_team_by_id)

    print()

    # Display NFC seeding
    print(f"{Colors.BOLD}{Colors.GREEN}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}                         NFC                              {Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'═' * 60}{Colors.RESET}\n")

    _display_conference_seeding(seeding_data.nfc, get_team_by_id)

    print(f"\n{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}\n")


def _display_conference_seeding(conference_data: Any, get_team_func: Any) -> None:
    """
    Helper function to display playoff seeding for a single conference.

    Args:
        conference_data: ConferenceSeeding object
        get_team_func: Function to get team name from ID
    """
    seeds = conference_data.seeds

    # Display seeds 1-4 (Division Winners)
    print(f"{Colors.BOLD}Division Winners:{Colors.RESET}")
    for seed_data in seeds[:4]:
        seed = seed_data.seed
        team_id = seed_data.team_id
        record = seed_data.record_string
        division = seed_data.division_name

        # Get team name
        try:
            team_name = str(get_team_func(team_id))[:25]
        except:
            team_name = f"Team {team_id}"[:25]

        # Color code by seed
        if seed == 1:
            color = Colors.BRIGHT_GREEN
            emoji = "👑"  # #1 seed gets bye
        elif seed == 2:
            color = Colors.GREEN
            emoji = "🏆"
        elif seed == 3:
            color = Colors.BRIGHT_YELLOW
            emoji = "🏆"
        else:
            color = Colors.YELLOW
            emoji = "🏆"

        print(f"  {color}{emoji} {seed}. {team_name:25s}  {record:8s}  ({division}){Colors.RESET}")

    # Display seeds 5-7 (Wild Cards)
    print(f"\n{Colors.BOLD}Wild Card:{Colors.RESET}")
    for seed_data in seeds[4:]:
        seed = seed_data.seed
        team_id = seed_data.team_id
        record = seed_data.record_string
        division = seed_data.division_name

        # Get team name
        try:
            team_name = str(get_team_func(team_id))[:25]
        except:
            team_name = f"Team {team_id}"[:25]

        # Wild cards get different color
        color = Colors.CYAN
        emoji = "🎫"

        print(f"  {color}{emoji} {seed}. {team_name:25s}  {record:8s}  ({division}){Colors.RESET}")


# Example usage and testing
if __name__ == "__main__":
    print_banner()

    # Test status display
    print_status("Wild Card Round", 2, 4)

    # Test menu
    display_playoff_menu("wild_card")

    # Test progress bar
    print("\nProgress Bar Example:")
    print(progress_bar(7, 11, label="Playoff Games"))

    # Test message functions
    print_success("Wild Card Round completed!")
    print_info("Advancing to Divisional Round...")
    print_warning("Low disk space detected")
    print_error("Failed to load bracket")

    print_separator()
    print(f"\n{Colors.BOLD}Playoff display utilities loaded successfully!{Colors.RESET}\n")
