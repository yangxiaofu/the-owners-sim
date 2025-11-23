# Draft Interactive Display System - Implementation Guide

**Status**: Implementation Reference
**Last Updated**: November 22, 2025
**Purpose**: Code templates, examples, and quick-start guide

---

## 1. Quick Start - Copy & Paste Code

### 1.1 Colors Module (src/draft/display/colors.py)

```python
"""Color codes and styling for draft display."""

class DraftColors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'      # Magenta - main titles
    OKBLUE = '\033[94m'      # Blue - conference losers
    OKCYAN = '\033[96m'      # Cyan - divisional losers
    OKGREEN = '\033[92m'     # Green - super bowl loser
    WARNING = '\033[93m'     # Yellow - wild card losers
    FAIL = '\033[91m'        # Red - non-playoff teams
    BOLD = '\033[1m'         # Bold text
    DIM = '\033[2m'          # Dim text
    UNDERLINE = '\033[4m'    # Underline
    ENDC = '\033[0m'         # Reset all

class MinimalColors:
    """Minimal styling for terminals without color support"""
    EMPHASIS = '\033[1m'     # Bold only
    DIM = '\033[2m'          # Dim
    UNDERLINE = '\033[4m'    # Underline
    ENDC = '\033[0m'         # Reset

def get_category_color(category: str) -> str:
    """
    Get color for pick category.

    Args:
        category: One of 'non_playoff', 'wild_card', 'divisional',
                  'conference', 'super_bowl_loss', 'super_bowl_win'

    Returns:
        ANSI color code string
    """
    color_map = {
        'non_playoff': DraftColors.FAIL,
        'wild_card': DraftColors.WARNING,
        'divisional': DraftColors.OKCYAN,
        'conference': DraftColors.OKBLUE,
        'super_bowl_loss': DraftColors.OKGREEN,
        'super_bowl_win': DraftColors.HEADER
    }
    return color_map.get(category, DraftColors.ENDC)

def apply_color(text: str, color: str) -> str:
    """Apply ANSI color to text."""
    return f"{color}{text}{DraftColors.ENDC}"

def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)
```

### 1.2 Headers Module (src/draft/display/headers.py)

```python
"""ASCII art headers and dividers for draft display."""

from .colors import DraftColors

def create_main_header(round_num: int = 0, width: int = 95) -> str:
    """
    Create main draft header.

    Args:
        round_num: Round number (0 = starts, 1-7 = during draft)
        width: Display width

    Returns:
        Formatted header string
    """
    if round_num == 0:
        title = "2025 NFL DRAFT - BEGINS NOW"
    elif round_num == -1:
        title = "2025 NFL DRAFT - COMPLETE"
    else:
        title = f"2025 NFL DRAFT - ROUND {round_num}"

    # Create border
    border = '═' * width
    # Center title (accounting for ANSI codes in length calc)
    padding = (width - len(title)) // 2
    title_line = ' ' * padding + title

    return (
        f"{DraftColors.BOLD}{border}{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}{DraftColors.HEADER}{title_line}{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}{border}{DraftColors.ENDC}"
    )

def create_category_header(category: str, pick_range: str, width: int = 95) -> str:
    """
    Create category section header.

    Args:
        category: Category name (e.g., "NON-PLAYOFF TEAMS")
        pick_range: Pick range string (e.g., "Picks 1-18")
        width: Display width

    Returns:
        Formatted header string
    """
    header_text = f"{category} ({pick_range})"
    color = {
        'non_playoff': DraftColors.FAIL,
        'wild_card': DraftColors.WARNING,
        'divisional': DraftColors.OKCYAN,
        'conference': DraftColors.OKBLUE,
        'super_bowl_loss': DraftColors.OKGREEN,
        'super_bowl_win': DraftColors.HEADER
    }.get(category.lower(), DraftColors.ENDC)

    return (
        f"\n{color}{DraftColors.BOLD}{header_text}{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}{'-' * width}{DraftColors.ENDC}"
    )

def create_column_headers(width: int = 95) -> str:
    """Create table column headers."""
    headers = [
        ('Pick', 6, 'right'),
        ('Team Name', 28, 'left'),
        ('Record', 12, 'center'),
        ('SOS', 8, 'right'),
        ('Reason', 25, 'left')
    ]

    line = ""
    for label, col_width, alignment in headers:
        if alignment == 'left':
            line += label.ljust(col_width)
        elif alignment == 'right':
            line += label.rjust(col_width)
        else:  # center
            line += label.center(col_width)

    return f"{DraftColors.BOLD}{line}{DraftColors.ENDC}\n{DraftColors.BOLD}{'-' * width}{DraftColors.ENDC}"

def create_divider(width: int = 95, style: str = 'heavy') -> str:
    """Create a divider line."""
    if style == 'heavy':
        char = '═'
    elif style == 'light':
        char = '─'
    elif style == 'double':
        char = '═'
    else:
        char = '-'

    return f"{DraftColors.BOLD}{char * width}{DraftColors.ENDC}"

def create_section_footer(section_name: str, pick_count: int, width: int = 95) -> str:
    """Create footer for a section."""
    footer_text = f"[{section_name} COMPLETE - {pick_count} picks made]"
    padding = (width - len(footer_text)) // 2

    return (
        f"\n{DraftColors.BOLD}{create_divider(width)}{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}" + ' ' * padding + footer_text +
        f"{DraftColors.ENDC}"
    )

def create_pause_prompt(round_num: int, width: int = 95) -> str:
    """Create interactive pause prompt."""
    prompt = (
        f"\n{DraftColors.BOLD}╔{'═' * (width - 2)}╗{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{' ' * (width - 2)}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{DraftColors.ENDC} "
        f"{DraftColors.BOLD}✓ ROUND {round_num} COMPLETE{DraftColors.ENDC}"
        f"{' ' * (width - 28)}"
        f"{DraftColors.BOLD}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{' ' * (width - 2)}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{DraftColors.ENDC} "
        f"{DraftColors.BOLD}Available actions:{DraftColors.ENDC}"
        f"{' ' * (width - 38)}"
        f"{DraftColors.BOLD}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{DraftColors.ENDC} "
        f"{DraftColors.OKGREEN}• [ENTER]{DraftColors.ENDC}  Continue to Round {round_num + 1}"
        f"{' ' * (width - 53)}"
        f"{DraftColors.BOLD}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{DraftColors.ENDC} "
        f"{DraftColors.OKGREEN}• [R]{DraftColors.ENDC}      Review previous picks"
        f"{' ' * (width - 38)}"
        f"{DraftColors.BOLD}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{DraftColors.ENDC} "
        f"{DraftColors.OKGREEN}• [S]{DraftColors.ENDC}      Show draft summary"
        f"{' ' * (width - 38)}"
        f"{DraftColors.BOLD}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{DraftColors.ENDC} "
        f"{DraftColors.OKGREEN}• [T]{DraftColors.ENDC}      Show your team's picks"
        f"{' ' * (width - 42)}"
        f"{DraftColors.BOLD}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{DraftColors.ENDC} "
        f"{DraftColors.OKGREEN}• [Q]{DraftColors.ENDC}      Quit draft"
        f"{' ' * (width - 32)}"
        f"{DraftColors.BOLD}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}║{' ' * (width - 2)}║{DraftColors.ENDC}\n"
        f"{DraftColors.BOLD}╚{'═' * (width - 2)}╝{DraftColors.ENDC}\n"
    )

    return prompt
```

### 1.3 Formatter Module (src/draft/display/formatter.py)

```python
"""Formatting functions for draft display."""

from typing import List, Tuple
from dataclasses import dataclass
from .colors import DraftColors, strip_ansi_codes, get_category_color
from .headers import create_column_headers

@dataclass
class DraftPick:
    """Data class for a single draft pick"""
    overall_pick: int
    pick_in_round: int
    round_number: int
    team_id: int
    team_name: str
    record: str
    strength_of_schedule: float
    category: str
    player_name: str = ""
    position: str = ""

def format_pick_row(pick: DraftPick, width: int = 95) -> str:
    """
    Format a single pick row with colors and alignment.

    Args:
        pick: DraftPick object
        width: Display width

    Returns:
        Formatted row string
    """
    color = get_category_color(pick.category)

    # Format each column
    pick_str = f"{pick.pick_in_round} (#{pick.overall_pick})"
    pick_col = f"{color}{pick_str.rjust(6)}{DraftColors.ENDC}"

    team_col = f"{color}{DraftColors.BOLD}{pick.team_name.ljust(28)}{DraftColors.ENDC}"

    record_col = f"{pick.record.center(12)}"

    sos_col = f"{pick.strength_of_schedule:.3f}".rjust(8)

    reason_col = f"{color}{pick.category.replace('_', ' ').title().ljust(25)}{DraftColors.ENDC}"

    # Combine with spacing
    row = f"{pick_col} {team_col} {record_col}    {sos_col}    {reason_col}"

    return row

def format_summary_row(team_id: int, team_name: str, pick_num: int,
                       player_name: str = "", position: str = "") -> str:
    """Format a pick for summary display."""
    if player_name and position:
        return (
            f"#{pick_num:2d}  {team_name:<25} {position:<5}  {player_name}"
        )
    else:
        return f"#{pick_num:2d}  {team_name:<25} (TBD)"

def center_text(text: str, width: int, fill_char: str = ' ') -> str:
    """Center text within specified width, accounting for ANSI codes."""
    clean_text = strip_ansi_codes(text)
    padding = max(0, (width - len(clean_text)) // 2)
    return fill_char * padding + text

def right_align_text(text: str, width: int) -> str:
    """Right-align text within specified width."""
    clean_text = strip_ansi_codes(text)
    padding = max(0, width - len(clean_text))
    return ' ' * padding + text

def left_align_text(text: str, width: int) -> str:
    """Left-align text within specified width."""
    clean_text = strip_ansi_codes(text)
    padding = max(0, width - len(clean_text))
    return text + ' ' * padding

def format_stats_block(stats: dict, width: int = 95) -> str:
    """
    Format statistics display block.

    Args:
        stats: Dictionary of statistic key-value pairs
        width: Display width

    Returns:
        Formatted stats block
    """
    output = ""
    output += f"{DraftColors.BOLD}{'DRAFT STATISTICS':^{width}}{DraftColors.ENDC}\n"
    output += f"{DraftColors.BOLD}{'-' * width}{DraftColors.ENDC}\n"

    # Format stats in 2 columns
    items = list(stats.items())
    for i in range(0, len(items), 2):
        key1, val1 = items[i]
        output += f"{key1:<30} {str(val1):<30}"

        if i + 1 < len(items):
            key2, val2 = items[i + 1]
            output += f"  {key2:<25} {str(val2)}\n"
        else:
            output += "\n"

    return output
```

### 1.4 Interactive Module (src/draft/display/interactive.py)

```python
"""Interactive input and prompts for draft display."""

from .colors import DraftColors

def get_pause_input(round_num: int, total_rounds: int = 7) -> str:
    """
    Get validated input at round pause.

    Args:
        round_num: Current round number
        total_rounds: Total rounds in draft

    Returns:
        Validated user choice
    """
    valid_options = ['', 'r', 's', 't', 'q']

    while True:
        try:
            user_input = input(
                f"\n{DraftColors.BOLD}Choice: {DraftColors.ENDC}"
            ).strip().lower()

            if user_input in valid_options:
                return user_input

            # Invalid input
            print(
                f"\n{DraftColors.FAIL}Invalid choice: '{user_input}'{DraftColors.ENDC}"
            )
            print(
                f"{DraftColors.OKGREEN}Valid options: "
                f"[ENTER] R S T Q{DraftColors.ENDC}\n"
            )

        except KeyboardInterrupt:
            print(f"\n{DraftColors.WARNING}Draft interrupted by user{DraftColors.ENDC}")
            return 'q'

def wait_for_continue(message: str = "Press ENTER to continue...") -> bool:
    """
    Wait for user to press ENTER.

    Args:
        message: Prompt message

    Returns:
        False if user quit (Ctrl+C), True otherwise
    """
    try:
        input(f"\n{DraftColors.BOLD}{message}{DraftColors.ENDC}")
        return True
    except KeyboardInterrupt:
        print(f"\n{DraftColors.WARNING}Operation cancelled{DraftColors.ENDC}")
        return False

def confirm_action(message: str) -> bool:
    """
    Get yes/no confirmation from user.

    Args:
        message: Confirmation message

    Returns:
        True for yes, False for no
    """
    while True:
        response = input(
            f"\n{DraftColors.BOLD}{message} (y/n): {DraftColors.ENDC}"
        ).strip().lower()

        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print(f"{DraftColors.FAIL}Please enter 'y' or 'n'{DraftColors.ENDC}")

def show_loading_animation(message: str, duration_seconds: float = 2.0):
    """
    Show animated loading spinner.

    Args:
        message: Message to display
        duration_seconds: How long to animate
    """
    import time
    import sys

    frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    end_time = time.time() + duration_seconds
    frame_idx = 0

    while time.time() < end_time:
        frame = frames[frame_idx % len(frames)]
        sys.stdout.write(f"\r{message} {frame}")
        sys.stdout.flush()
        time.sleep(0.1)
        frame_idx += 1

    sys.stdout.write(f"\r{message} ✓\n")
    sys.stdout.flush()

def get_team_choice(teams: list, prompt: str = "Select team") -> int:
    """
    Get team selection from user.

    Args:
        teams: List of team IDs
        prompt: Prompt message

    Returns:
        Selected team ID
    """
    while True:
        try:
            choice = int(input(
                f"\n{DraftColors.BOLD}{prompt} (1-32): {DraftColors.ENDC}"
            ))

            if 1 <= choice <= 32:
                return choice

            print(f"{DraftColors.FAIL}Invalid team ID. Must be 1-32.{DraftColors.ENDC}")

        except ValueError:
            print(f"{DraftColors.FAIL}Please enter a valid number.{DraftColors.ENDC}")
        except KeyboardInterrupt:
            print(f"\n{DraftColors.WARNING}Selection cancelled{DraftColors.ENDC}")
            return None
```

---

## 2. Example: Complete Round Display Function

```python
"""Example: Display a complete round of picks"""

from draft.display.headers import (
    create_main_header,
    create_category_header,
    create_column_headers,
    create_divider,
    create_section_footer
)
from draft.display.formatter import format_pick_row, DraftPick
from draft.display.colors import DraftColors

def display_round(round_num: int, picks: List[DraftPick], width: int = 95):
    """Display all picks for a round"""

    # Main header
    print(f"\n{create_main_header(round_num, width)}\n")

    # Group picks by category
    categories = {
        'non_playoff': (picks[:18], 'NON-PLAYOFF TEAMS', 'Picks 1-18'),
        'wild_card': (picks[18:24], 'WILD CARD LOSERS', 'Picks 19-24'),
        'divisional': (picks[24:28], 'DIVISIONAL LOSERS', 'Picks 25-28'),
        'conference': (picks[28:30], 'CONFERENCE LOSERS', 'Picks 29-30'),
        'super_bowl_loss': (picks[30:31], 'CHAMPIONSHIP FINALISTS', 'Pick 31'),
        'super_bowl_win': (picks[31:32], 'CHAMPIONSHIP FINALISTS', 'Pick 32'),
    }

    # Display each category
    for category_key, (category_picks, category_name, pick_range) in categories.items():
        if not category_picks:
            continue

        # Category header
        print(create_category_header(category_key, pick_range, width))
        print(f"{create_column_headers(width)}\n")

        # Picks in this category
        for pick in category_picks:
            print(format_pick_row(pick, width))

        print()  # Blank line after category

    # Footer
    total_picks = len(picks)
    print(create_section_footer(f"ROUND {round_num}", total_picks, width))
```

---

## 3. Example: Summary Statistics Display

```python
"""Example: Display draft summary statistics"""

from dataclasses import dataclass
from typing import List, Dict
from draft.display.headers import create_main_header, create_divider
from draft.display.colors import DraftColors

@dataclass
class DraftStats:
    """Draft statistics"""
    total_picks: int
    picks_by_position: Dict[str, int]
    rounds_completed: int
    total_rounds: int
    avg_pick_time_seconds: float
    team_picks: Dict[int, List[int]]  # team_id -> list of pick numbers

def display_draft_summary(stats: DraftStats, width: int = 95):
    """Display comprehensive draft summary"""

    print(f"\n{create_main_header(-1, width)}\n")  # -1 for COMPLETE

    # Overview section
    print(f"\n{DraftColors.BOLD}OVERVIEW{DraftColors.ENDC}")
    print(f"{DraftColors.BOLD}{'-' * width}{DraftColors.ENDC}")
    print(f"Total Picks Made:           {stats.total_picks} (7 rounds × 32 teams)")
    print(f"Average Time per Pick:      {stats.avg_pick_time_seconds:.1f} seconds")
    print(f"Estimated Total Duration:   {(stats.total_picks * stats.avg_pick_time_seconds / 60):.1f} minutes")

    # Round 1 breakdown
    print(f"\n{DraftColors.BOLD}ROUND 1 BREAKDOWN{DraftColors.ENDC}")
    print(f"{DraftColors.BOLD}{'-' * width}{DraftColors.ENDC}")
    print(f"{DraftColors.FAIL}Non-Playoff Teams:          {18} picks (Picks 1-18){DraftColors.ENDC}")
    print(f"{DraftColors.WARNING}Wild Card Losers:           {6} picks (Picks 19-24){DraftColors.ENDC}")
    print(f"{DraftColors.OKCYAN}Divisional Losers:          {4} picks (Picks 25-28){DraftColors.ENDC}")
    print(f"{DraftColors.OKBLUE}Conference Losers:          {2} picks (Picks 29-30){DraftColors.ENDC}")
    print(f"{DraftColors.OKGREEN}Super Bowl Loser:           {1} pick (Pick 31){DraftColors.ENDC}")
    print(f"{DraftColors.HEADER}Super Bowl Winner:          {1} pick (Pick 32){DraftColors.ENDC}")

    # Positional breakdown
    print(f"\n{DraftColors.BOLD}POSITIONAL BREAKDOWN (ALL ROUNDS){DraftColors.ENDC}")
    print(f"{DraftColors.BOLD}{'-' * width}{DraftColors.ENDC}")

    sorted_positions = sorted(
        stats.picks_by_position.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for position, count in sorted_positions:
        percentage = (count / stats.total_picks) * 100
        bar_length = int(percentage / 2)  # 50-char max bar
        bar = '█' * bar_length
        print(f"{position:<4} {count:3d} picks ({percentage:5.1f}%)  {bar}")

    print(f"\n{create_divider(width)}\n")
```

---

## 4. Example: Interactive Main Loop

```python
"""Example: Main interactive draft simulation loop"""

from draft.display.headers import create_pause_prompt
from draft.display.interactive import (
    get_pause_input,
    wait_for_continue,
    show_loading_animation
)
from draft.display.colors import DraftColors

def run_draft_simulation():
    """Main draft simulation loop"""

    total_rounds = 7
    picks_per_round = 32
    all_picks = []

    for round_num in range(1, total_rounds + 1):
        # Display round
        display_round(round_num, all_picks, width=95)

        # Generate picks for this round
        for pick_num in range(1, picks_per_round + 1):
            # Show pick being analyzed
            print(
                f"\n{DraftColors.BOLD}🏈 ROUND {round_num} - "
                f"Pick {pick_num} of {picks_per_round}{DraftColors.ENDC}"
            )

            # Show AI analysis animation
            show_loading_animation(
                f"{DraftColors.OKCYAN}AI analyzing...{DraftColors.ENDC}",
                duration_seconds=1.5
            )

            # Simulate pick selection
            pick = simulate_pick_selection(round_num, pick_num)
            all_picks.append(pick)

            # Small pause before next pick
            import time
            time.sleep(0.5)

        # End of round - show pause prompt
        while True:
            print(create_pause_prompt(round_num, width=95))

            choice = get_pause_input(round_num, total_rounds)

            if choice == '':  # Continue
                break
            elif choice == 'r':  # Review
                display_previous_round(round_num - 1, all_picks)
                wait_for_continue()
            elif choice == 's':  # Summary
                display_draft_summary(calculate_stats(all_picks))
                wait_for_continue()
            elif choice == 't':  # Team picks
                team_id = get_team_choice(list(range(1, 33)))
                if team_id:
                    display_team_picks(team_id, all_picks)
                    wait_for_continue()
            elif choice == 'q':  # Quit
                print(f"\n{DraftColors.OKGREEN}Exiting draft. Thanks for viewing!{DraftColors.ENDC}\n")
                return

    # Final summary
    print(f"\n{DraftColors.HEADER}{'='*95}{DraftColors.ENDC}")
    print(f"{DraftColors.HEADER}DRAFT COMPLETE!{DraftColors.ENDC}")
    print(f"{DraftColors.HEADER}{'='*95}{DraftColors.ENDC}\n")

    display_draft_summary(calculate_stats(all_picks))

    wait_for_continue("Press ENTER to return to main menu...")
```

---

## 5. Terminal Width Detection

```python
"""Terminal width detection and adaptation"""

import shutil
import sys
from .colors import detect_color_support

class TerminalConfig:
    """Terminal configuration detection"""

    @staticmethod
    def detect_width() -> int:
        """Detect terminal width and return safe display width"""
        try:
            cols = shutil.get_terminal_size().columns
        except:
            cols = 80  # Default fallback

        if cols >= 120:
            return 120
        elif cols >= 95:
            return 95
        elif cols >= 80:
            return 80
        else:
            # Very narrow terminal
            return 70

    @staticmethod
    def detect_unicode_support() -> bool:
        """Detect if terminal supports Unicode"""
        try:
            # Try to encode a Unicode character
            sys.stdout.encoding.encode('─')
            return True
        except:
            return False

    @staticmethod
    def detect_color_support() -> bool:
        """Detect if terminal supports ANSI colors"""
        import os

        # Check NO_COLOR environment variable
        if os.environ.get('NO_COLOR'):
            return False

        # Check if stdout is a TTY
        return sys.stdout.isatty()

    @staticmethod
    def get_config():
        """Get complete terminal configuration"""
        return {
            'width': TerminalConfig.detect_width(),
            'unicode': TerminalConfig.detect_unicode_support(),
            'color': TerminalConfig.detect_color_support(),
        }
```

---

## 6. Configuration YAML Example

```yaml
# src/config/draft_display_config.yaml

display:
  # Width: 80 (safe minimum), 95 (standard), 120 (wide)
  width: 95
  max_width: 120
  min_width: 80

  # Auto-detect width from terminal
  auto_detect_width: true

  # Color scheme: standard, minimal, dark, none
  color_scheme: "standard"

  # Use Unicode characters (═, ─, etc)
  use_unicode: true

  # Fallback to ASCII if Unicode unavailable
  unicode_fallback: true

animation:
  # Pause between picks (milliseconds)
  pick_pause_ms: 500

  # Selection animation duration
  selection_animation_ms: 1500

  # Spinner frame rate (Hz)
  frame_rate: 10

  # Show spinner animation
  show_spinner: true

interactive:
  # Auto-advance picks without pause
  auto_advance_picks: false

  # Auto-advance rounds without pause
  auto_advance_rounds: false

  # Pause after each round
  pause_after_round: true

  # Allow user review of previous picks
  allow_review: true

  # Allow draft statistics display
  allow_statistics: true

  # Allow team pick filtering
  allow_team_filter: true

  # Input timeout (seconds)
  input_timeout_seconds: 0  # 0 = no timeout

statistics:
  # Show summary after draft completes
  show_summary: true

  # Show team-specific summary
  show_team_summary: true

  # Show positional breakdown
  show_positional_breakdown: true

  # Detail level: full, compact, minimal
  detail_level: "full"

  # Show top 10 picks
  show_top_picks: true

  # Show speed statistics
  show_speed_stats: true

logging:
  # Log all picks to file
  log_picks: true

  # Log file path (relative to project root)
  log_path: "data/draft_simulation.log"

  # Verbose logging
  verbose: false
```

---

## 7. Quick Reference - Function Signatures

```python
# colors.py
get_category_color(category: str) -> str
apply_color(text: str, color: str) -> str
strip_ansi_codes(text: str) -> str

# headers.py
create_main_header(round_num: int, width: int) -> str
create_category_header(category: str, pick_range: str, width: int) -> str
create_column_headers(width: int) -> str
create_divider(width: int, style: str) -> str
create_section_footer(section_name: str, pick_count: int, width: int) -> str
create_pause_prompt(round_num: int, width: int) -> str

# formatter.py
format_pick_row(pick: DraftPick, width: int) -> str
format_summary_row(team_id: int, team_name: str, pick_num: int, ...) -> str
center_text(text: str, width: int) -> str
left_align_text(text: str, width: int) -> str
right_align_text(text: str, width: int) -> str
format_stats_block(stats: dict, width: int) -> str

# interactive.py
get_pause_input(round_num: int, total_rounds: int) -> str
wait_for_continue(message: str) -> bool
confirm_action(message: str) -> bool
show_loading_animation(message: str, duration_seconds: float) -> None
get_team_choice(teams: list) -> int

# terminal_config.py
TerminalConfig.detect_width() -> int
TerminalConfig.detect_unicode_support() -> bool
TerminalConfig.detect_color_support() -> bool
TerminalConfig.get_config() -> dict
```

---

## 8. Testing Checklist

```python
# tests/draft/test_display.py

def test_colors_applied_correctly():
    """ANSI codes should be present"""
    assert '\033[' in DraftColors.HEADER

def test_column_widths():
    """Formatted rows should be correct width"""
    pick = create_sample_pick()
    output = format_pick_row(pick)
    clean = strip_ansi_codes(output)
    assert len(clean) == 95

def test_unicode_fallback():
    """Should not crash without Unicode"""
    header = create_main_header(1, unicode_support=False)
    assert header  # Should return something

def test_pause_input_validation():
    """Should only accept valid inputs"""
    # Mock input to return 'R'
    with patch('builtins.input', return_value='R'):
        result = get_pause_input(1)
        assert result == 'r'  # Should lowercase

def test_terminal_width_detection():
    """Should detect terminal width"""
    width = TerminalConfig.detect_width()
    assert width in [70, 80, 95, 120]

def test_color_terminal_detection():
    """Should detect color support"""
    supports_color = TerminalConfig.detect_color_support()
    assert isinstance(supports_color, bool)

def test_long_team_name_handling():
    """Should handle names longer than column width"""
    long_name = "A" * 50
    pick = DraftPick(..., team_name=long_name)
    output = format_pick_row(pick)
    # Should not crash
    assert output

def test_stats_block_formatting():
    """Statistics block should format correctly"""
    stats = {
        'Total Picks': 262,
        'Picks Made': 100,
        'Completion': '38.2%',
    }
    output = format_stats_block(stats)
    assert 'Total Picks' in output
    assert 'STATISTICS' in output
```

---

## 9. Performance Targets

| Operation | Target | Notes |
|---|---|---|
| Format single pick | <1ms | Must be fast for 262 picks |
| Render full round | <100ms | 32 picks at once |
| Pause prompt display | <50ms | Should be instant |
| Statistics block | <50ms | No DB queries |
| Animation frame | <100ms | Spinner animation smooth |
| Input response | <100ms | Must be responsive |

---

## 10. Deployment Checklist

- [ ] All modules created under `src/draft/display/`
- [ ] Configuration file created: `src/config/draft_display_config.yaml`
- [ ] Tests created: `tests/draft/test_display.py`
- [ ] Terminal detection tested on multiple terminals
- [ ] Color support tested with/without ANSI
- [ ] Unicode fallback tested
- [ ] Performance verified (<100ms per round render)
- [ ] Documentation created in `docs/DRAFT_INTERACTIVE_DISPLAY_SYSTEM.md`
- [ ] Demo created: `demo/draft_simulation_demo/`
- [ ] Integration tested with draft simulator
- [ ] User acceptance testing completed

---

**End of Implementation Guide**
