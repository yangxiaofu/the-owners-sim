#!/usr/bin/env python3
"""
Interactive Full Season Simulator

Terminal-based interactive NFL full season simulation from Week 1 through Super Bowl and offseason.
Provides comprehensive phase-aware controls for regular season, playoffs, and offseason.

Commands vary by phase:

REGULAR SEASON:
  [1] Advance 1 day0
  [2] Advance 7 days (1 week)
  [3] Simulate to end of regular season
  [4] Show current standings
  [5] Show upcoming games
  [6] View playoff picture (Week 10+)
  [0] Exit

PLAYOFFS:
  [1] Advance 1 day
  [2] Advance 7 days (1 week)
  [3] Complete current playoff round
  [4] Show playoff bracket
  [5] Show completed games
  [6] Simulate to Super Bowl
  [0] Exit

OFFSEASON:
  [1] View season summary
  [2] View Super Bowl champion
  [3] View regular season stat leaders
  [4] View playoff stat leaders
  [0] Exit
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from calendar.date_models import Date
from season.season_cycle_controller import SeasonCycleController

# Handle both direct execution and module import for display utilities
try:
    from .display_utils import *
except ImportError:
    # Direct execution - use absolute imports
    from display_utils import *


class InteractiveFullSeasonSimulator:
    """

    Interactive terminal interface for full season simulation.

    Provides phase-aware user control over complete NFL season:
    - Regular Season (272 games over 18 weeks)
    - Playoffs (13 games: Wild Card → Super Bowl)
    - Offseason (summary and stat viewing)

    Features automatic phase transitions with user notifications.
    """

    def __init__(
        self,
        dynasty_id: str,
        database_path: str = None
    ):
        """
        Initialize interactive full season simulator.

        Args:
            dynasty_id: Unique dynasty identifier for data isolation
            database_path: Path to database (defaults to data/full_season_2024.db)
        """
        print_info("Initializing Interactive Full Season Simulator...")

        # Use absolute path for database to avoid duplicate databases
        if database_path is None:
            database_path = str(Path(__file__).parent / "data" / "full_season_2024.db")

        # Store dynasty ID
        self.dynasty_id = dynasty_id

        # Create season cycle controller
        try:
            self.controller = SeasonCycleController(
                database_path=database_path,
                dynasty_id=dynasty_id,
                season_year=2024,
                start_date=Date(2024, 9, 4),  # September 4, 2024 (Wednesday - day before first game)
                enable_persistence=True,
                verbose_logging=True
            )
            print_success("Season cycle controller initialized successfully")
        except Exception as e:
            print_error(f"Failed to initialize controller: {e}")
            raise

        self.running = True
        self.database_path = database_path

        # Initialize logger
        import logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        """Main terminal loop with phase-aware menu."""
        clear_screen()
        print_banner()

        print_success("Welcome to the Interactive NFL Full Season Simulator!")
        print_info(f"Database: {self.database_path}")
        print_separator()

        input("\nPress Enter to begin...")

        while self.running:
            clear_screen()
            print_banner()

            # Display current status
            try:
                self.display_current_status()
            except Exception as e:
                print_error(f"Error displaying status: {e}")

            # Get current phase for menu display
            try:
                current_phase = self.controller.get_current_phase()
                phase_name = current_phase.value
            except:
                phase_name = "unknown"

            # Display phase-aware menu
            self.print_phase_menu(phase_name)

            # Get user input
            try:
                choice = input("\n" + Colors.BRIGHT_CYAN + "Enter command: " + Colors.RESET).strip()

                # Handle command based on phase
                self.handle_command(choice, phase_name)

            except KeyboardInterrupt:
                print("\n")
                self.handle_exit()
                break
            except Exception as e:
                print_error(f"Error processing command: {e}")
                input("\nPress Enter to continue...")

    def display_current_status(self):
        """Display current simulation status with phase information."""
        # Display dynasty info
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}🏆 Dynasty: {self.dynasty_id}{Colors.RESET}")

        # Get current state
        state = self.controller.get_current_state()
        current_phase = self.controller.get_current_phase()

        # Display phase-specific status
        print(f"\n{Colors.BOLD}{Colors.CYAN}═══ FULL SEASON STATUS ═══{Colors.RESET}")
        print(f"📅 Current Date: {Colors.BOLD}{state['current_date']}{Colors.RESET}")
        print(f"🏈 Current Phase: {Colors.BOLD}{Colors.YELLOW}{current_phase.value.replace('_', ' ').title()}{Colors.RESET}")
        print(f"✅ Total Games Played: {Colors.BOLD}{state['total_games_played']}{Colors.RESET} / 285 (272 regular + 13 playoff)")
        print(f"📊 Days Simulated: {Colors.BOLD}{state['total_days_simulated']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'═' * 40}{Colors.RESET}\n")

        # Show phase-specific progress
        if current_phase.value == "regular_season":
            # Regular season progress
            games_played = state['total_games_played']
            progress = progress_bar(games_played, 272, width=50, label="Regular Season")
            print(f"{progress}\n")
        elif current_phase.value == "playoffs":
            # Playoff progress
            playoff_games = state['total_games_played'] - 272  # Assuming 272 regular season games completed
            progress = progress_bar(playoff_games, 13, width=50, label="Playoffs")
            print(f"{progress}\n")

    def print_phase_menu(self, phase_name: str):
        """
        Display phase-aware command menu.

        Args:
            phase_name: Current phase name (regular_season, playoffs, offseason)
        """
        if phase_name == "regular_season":
            self.print_regular_season_menu()
        elif phase_name == "playoffs":
            self.print_playoffs_menu()
        elif phase_name == "offseason":
            self.print_offseason_menu()
        else:
            print_warning(f"Unknown phase: {phase_name}")

    def print_regular_season_menu(self):
        """Display regular season command menu."""
        # Get current week for context
        try:
            state = self.controller.get_current_state()
            # Note: we'll need to get week from state once available
            week_info = ""
        except:
            week_info = ""

        print(f"\n{Colors.BOLD}{Colors.BRIGHT_YELLOW}╔═══ REGULAR SEASON MENU ═══╗{Colors.RESET}")
        print(f"{Colors.YELLOW}║{Colors.RESET}")
        print(f"{Colors.YELLOW}║{Colors.RESET}  1️⃣  Advance 1 day")
        print(f"{Colors.YELLOW}║{Colors.RESET}  2️⃣  Advance 7 days (1 week)")
        print(f"{Colors.YELLOW}║{Colors.RESET}  3️⃣  Simulate to end of regular season")
        print(f"{Colors.YELLOW}║{Colors.RESET}  4️⃣  Show current standings")
        print(f"{Colors.YELLOW}║{Colors.RESET}  5️⃣  Show upcoming games")
        print(f"{Colors.YELLOW}║{Colors.RESET}  6️⃣  View playoff picture (Week 10+)")
        print(f"{Colors.YELLOW}║{Colors.RESET}  0️⃣  Exit")
        print(f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}╚═══════════════════════════╝{Colors.RESET}\n")

    def print_playoffs_menu(self):
        """Display playoffs command menu."""
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}╔═══ PLAYOFFS MENU ═══╗{Colors.RESET}")
        print(f"{Colors.MAGENTA}║{Colors.RESET}")
        print(f"{Colors.MAGENTA}║{Colors.RESET}  1️⃣  Advance 1 day")
        print(f"{Colors.MAGENTA}║{Colors.RESET}  2️⃣  Advance 7 days (1 week)")
        print(f"{Colors.MAGENTA}║{Colors.RESET}  3️⃣  Complete current playoff round")
        print(f"{Colors.MAGENTA}║{Colors.RESET}  4️⃣  Show playoff bracket")
        print(f"{Colors.MAGENTA}║{Colors.RESET}  5️⃣  Show completed games")
        print(f"{Colors.MAGENTA}║{Colors.RESET}  {Colors.BRIGHT_GREEN}6️⃣  Simulate to Super Bowl{Colors.RESET}")
        print(f"{Colors.MAGENTA}║{Colors.RESET}  0️⃣  Exit")
        print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}╚═════════════════════╝{Colors.RESET}\n")

    def print_offseason_menu(self):
        """Display offseason command menu."""
        current_date = self.controller.calendar.get_current_date()
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_BLUE}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}[OFFSEASON MENU]{Colors.RESET}")
        print(f"{Colors.BLUE}Current Date: {current_date}{Colors.RESET}")
        print(f"{Colors.BLUE}Current Phase: Offseason{Colors.RESET}")

        print(f"\n{Colors.BOLD}📅 CALENDAR CONTROLS{Colors.RESET}")
        print(f"{Colors.BLUE}[1]{Colors.RESET} Advance 1 Day (trigger events for this date)")
        print(f"{Colors.BLUE}[2]{Colors.RESET} Advance 1 Week (trigger events across 7 days)")
        print(f"{Colors.BLUE}[3]{Colors.RESET} Advance to Next Event")

        print(f"\n{Colors.BOLD}📋 EVENT MANAGEMENT{Colors.RESET}")
        print(f"{Colors.BLUE}[4]{Colors.RESET} View Upcoming Events (next 10)")
        print(f"{Colors.BLUE}[5]{Colors.RESET} View Event History (last 10 triggered)")

        print(f"\n{Colors.BOLD}📊 SEASON REVIEW{Colors.RESET}")
        print(f"{Colors.BLUE}[6]{Colors.RESET} View Final Standings")
        print(f"{Colors.BLUE}[7]{Colors.RESET} View Season Summary")
        print(f"{Colors.BLUE}[8]{Colors.RESET} View Stat Leaders")

        print(f"\n{Colors.BLUE}[0]{Colors.RESET} Exit to Main Menu")
        print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}{'='*80}{Colors.RESET}\n")

    def handle_command(self, choice: str, phase_name: str):
        """
        Handle user command based on current phase.

        Args:
            choice: User's menu choice
            phase_name: Current phase name
        """
        if phase_name == "regular_season":
            self.handle_regular_season_command(choice)
        elif phase_name == "playoffs":
            self.handle_playoffs_command(choice)
        elif phase_name == "offseason":
            self.handle_offseason_command(choice)
        else:
            print_warning(f"Unknown phase: {phase_name}")
            input("\nPress Enter to continue...")

    # ========== REGULAR SEASON COMMANDS ==========

    def handle_regular_season_command(self, choice: str):
        """Handle commands during regular season phase."""
        if choice == "1":
            self.handle_advance_day()
        elif choice == "2":
            self.handle_advance_week()
        elif choice == "3":
            self.handle_simulate_regular_season()
        elif choice == "4":
            self.handle_show_standings()
        elif choice == "5":
            self.handle_show_upcoming()
        elif choice == "6":
            self.handle_view_playoff_picture()
        elif choice == "0":
            self.handle_exit()
        else:
            print_warning(f"Invalid command: {choice}")
            input("\nPress Enter to continue...")

    def handle_advance_day(self):
        """Advance 1 day and display results."""
        print_separator()
        print_info("Advancing 1 day...")

        try:
            result = self.controller.advance_day()

            # Display results
            if result.get('games_played', 0) > 0:
                print(f"\n{Colors.BOLD}Games played today: {result['games_played']}{Colors.RESET}")
                # TODO: Display game results when available
            else:
                print_info("No games scheduled today")

            # Check for phase transition
            if result.get('phase_transition'):
                self.display_phase_transition(result['phase_transition'])

        except Exception as e:
            print_error(f"Error advancing day: {e}")

        input("\nPress Enter to continue...")

    def handle_advance_week(self):
        """Advance 7 days and display weekly summary."""
        print_separator()
        print_info("Advancing 7 days (1 week)...")

        try:
            result = self.controller.advance_week()

            # Display weekly summary
            if result.get('total_games_played', 0) > 0:
                print(f"\n{Colors.BOLD}Week complete!{Colors.RESET}")
                print(f"Games played: {result['total_games_played']}")
            else:
                print_info("No games in this week")

            # Check for phase transition
            if result.get('phase_transition'):
                self.display_phase_transition(result['phase_transition'])

        except Exception as e:
            print_error(f"Error advancing week: {e}")

        input("\nPress Enter to continue...")

    def handle_simulate_regular_season(self):
        """Simulate to end of regular season."""
        print_separator()
        print_warning("⚠️  This will simulate the entire remaining regular season.")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm != 'y':
            print_info("Simulation cancelled")
            input("\nPress Enter to continue...")
            return

        print_separator()
        print_info("Simulating to end of regular season...")
        print_info("This may take several minutes...")
        print()

        try:
            # Simulate until playoffs or offseason
            iteration_count = 0
            while True:
                iteration_count += 1

                # DEBUG: Before advance
                print(f"\n{'─'*80}")
                print(f"🔍 DEBUG - Iteration {iteration_count}")
                print(f"{'─'*80}")
                print(f"   Current phase: {self.controller.get_current_phase().value}")
                print(f"   Total games: {self.controller.season_controller.total_games_played}/272")
                print(f"   Current week: {self.controller.season_controller.current_week}")
                print(f"   Is complete? {self.controller._is_regular_season_complete()}")

                result = self.controller.advance_week()

                # DEBUG: After advance
                print(f"\n   After advance_week():")
                print(f"   ├─ Games this week: {result.get('total_games_played', 0)}")
                print(f"   ├─ Total games now: {self.controller.season_controller.total_games_played}/272")
                print(f"   ├─ Current phase: {self.controller.get_current_phase().value}")
                print(f"   ├─ Phase transition: {result.get('phase_transition', 'None')}")

                # Check for errors in daily results
                if result.get('daily_results'):
                    error_count = 0
                    for day_result in result['daily_results']:
                        if day_result.get('errors'):
                            error_count += len(day_result['errors'])
                            for error in day_result['errors']:
                                print(f"   ├─ ❌ Error: {error}")
                    if error_count > 0:
                        print(f"   └─ Total errors this week: {error_count}")

                current_phase = self.controller.get_current_phase()

                if current_phase.value != "regular_season":
                    # Phase changed - we're done
                    print(f"\n✅ Phase changed to {current_phase.value}!")
                    if result.get('phase_transition'):
                        self.display_phase_transition(result['phase_transition'])
                    break

                # SAFETY: Break if no progress after 5 iterations
                if self.controller.season_controller.total_games_played == 0 and iteration_count >= 5:
                    print_error("\n🛑 SAFETY BREAK: 5 weeks simulated, 0 games played!")
                    print_error("This indicates games are not being simulated successfully.")
                    break

                # SAFETY: Break after 30 iterations (17 weeks + buffer for bye weeks)
                if iteration_count >= 30:
                    print_error("\n🛑 SAFETY BREAK: 30 iterations reached!")
                    print_error(f"Games played: {self.controller.season_controller.total_games_played}/272")
                    break

            print_success("Regular season complete!")

        except Exception as e:
            print_error(f"Error simulating season: {e}")

        input("\nPress Enter to continue...")

    def handle_show_standings(self):
        """Display current standings."""
        print_separator()
        print_info("Fetching current standings...")

        try:
            standings = self.controller.get_current_standings()
            display_standings(standings)

        except Exception as e:
            print_error(f"Error fetching standings: {e}")

        input("\nPress Enter to continue...")

    def handle_show_upcoming(self):
        """Display upcoming games."""
        print_separator()

        # Ask how many days ahead
        try:
            days_str = input("How many days ahead? (default 7): ").strip()
            days = int(days_str) if days_str else 7
        except ValueError:
            days = 7

        print_info(f"Fetching games for next {days} days...")

        try:
            # TODO: Implement get_upcoming_games when available
            print_info("Upcoming games feature coming soon")

        except Exception as e:
            print_error(f"Error fetching upcoming games: {e}")

        input("\nPress Enter to continue...")

    def handle_view_playoff_picture(self):
        """Display current playoff seeding."""
        print_separator()
        print_info("Calculating current playoff seeding...")

        try:
            # TODO: Check week number when available
            # For now, just try to get seeding
            # seeding_data = self.controller.get_playoff_seeding()
            print_info("Playoff picture feature coming soon")

        except Exception as e:
            print_error(f"Error fetching playoff seeding: {e}")

        input("\nPress Enter to continue...")

    # ========== PLAYOFFS COMMANDS ==========

    def handle_playoffs_command(self, choice: str):
        """Handle commands during playoffs phase."""
        if choice == "1":
            self.handle_advance_day()
        elif choice == "2":
            self.handle_advance_week()
        elif choice == "3":
            self.handle_complete_playoff_round()
        elif choice == "4":
            self.handle_show_bracket()
        elif choice == "5":
            self.handle_show_completed_games()
        elif choice == "6":
            self.handle_simulate_to_super_bowl()
        elif choice == "0":
            self.handle_exit()
        else:
            print_warning(f"Invalid command: {choice}")
            input("\nPress Enter to continue...")

    def handle_complete_playoff_round(self):
        """Complete current playoff round."""
        print_separator()
        print_info("Completing current playoff round...")

        try:
            # Advance until round completes
            # TODO: Implement round completion logic
            print_info("Playoff round completion coming soon")

        except Exception as e:
            print_error(f"Error completing round: {e}")

        input("\nPress Enter to continue...")

    def handle_show_bracket(self):
        """Display playoff bracket."""
        print_separator()
        print_info("Fetching playoff bracket...")

        try:
            bracket = self.controller.get_playoff_bracket()
            if bracket:
                # TODO: Use display function when available
                print_success("Playoff bracket retrieved")
            else:
                print_warning("Playoff bracket not available")

        except Exception as e:
            print_error(f"Error fetching bracket: {e}")

        input("\nPress Enter to continue...")

    def handle_show_completed_games(self):
        """Display completed playoff games."""
        print_separator()
        print_info("Fetching completed playoff games...")

        try:
            # TODO: Get completed games from controller
            print_info("Completed games display coming soon")

        except Exception as e:
            print_error(f"Error fetching games: {e}")

        input("\nPress Enter to continue...")

    def handle_simulate_to_super_bowl(self):
        """Simulate to Super Bowl."""
        print_separator()
        print_warning("⚠️  This will simulate all remaining playoff games through Super Bowl.")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm != 'y':
            print_info("Simulation cancelled")
            input("\nPress Enter to continue...")
            return

        print_separator()
        print_info("Simulating to Super Bowl...")
        print()

        try:
            # Simulate until offseason
            iteration_count = 0
            max_iterations = 10  # Safety limit (playoffs shouldn't take more than ~5-6 weeks)

            while True:
                iteration_count += 1
                result = self.controller.advance_week()
                current_phase = self.controller.get_current_phase()

                print(f"\n[DEBUG] Iteration {iteration_count}: Phase = {current_phase.value}, Games = {result.get('total_games_played', 0)}")

                if current_phase.value == "offseason":
                    # Super Bowl complete
                    if result.get('phase_transition'):
                        self.display_phase_transition(result['phase_transition'])
                    break

                # SAFETY: Prevent infinite loop
                if iteration_count >= max_iterations:
                    print_error(f"\n🛑 SAFETY BREAK: {max_iterations} weeks simulated without reaching offseason")
                    print_error("This may indicate Super Bowl didn't trigger phase transition")
                    print_info(f"Current phase: {current_phase.value}")
                    print_info(f"Last week games: {result.get('total_games_played', 0)}")
                    break

            print_success("Super Bowl complete!")

        except Exception as e:
            print_error(f"Error simulating playoffs: {e}")

        input("\nPress Enter to continue...")

    # ========== OFFSEASON COMMANDS ==========

    def handle_offseason_command(self, choice: str):
        """Handle commands during offseason phase."""
        if choice == "1":
            self.handle_offseason_advance_day()
        elif choice == "2":
            self.handle_offseason_advance_week()
        elif choice == "3":
            self.handle_advance_to_next_event()
        elif choice == "4":
            self.handle_view_upcoming_events()
        elif choice == "5":
            self.handle_view_event_history()
        elif choice == "6":
            self.handle_show_standings()
        elif choice == "7":
            self.handle_view_season_summary()
        elif choice == "8":
            self.handle_view_stat_leaders()
        elif choice == "0":
            self.handle_exit()
        else:
            print_warning(f"Invalid command: {choice}")
            input("\nPress Enter to continue...")

    def handle_offseason_advance_day(self):
        """Advance 1 day in offseason and display triggered events."""
        print_separator()
        print_info("Advancing 1 day...")

        try:
            result = self.controller.advance_day()
            print(f"\n✅ Advanced to {result['date']}")

            if result.get('events_triggered'):
                print(f"\n📅 Events Triggered:")
                self._display_triggered_events(result['events_triggered'])
            else:
                print_info("No events triggered today")

        except Exception as e:
            print_error(f"Error advancing day: {e}")

        input("\nPress Enter to continue...")

    def handle_offseason_advance_week(self):
        """Advance 7 days in offseason and display all triggered events."""
        print_separator()
        print_info("Advancing 7 days (1 week)...")

        try:
            all_events = []
            for i in range(7):
                result = self.controller.advance_day()
                if result.get('events_triggered'):
                    all_events.extend(result['events_triggered'])

            print(f"\n✅ Advanced 1 week to {self.controller.calendar.get_current_date()}")

            if all_events:
                print(f"\n📅 Events Triggered ({len(all_events)} total):")
                self._display_triggered_events(all_events)
            else:
                print_info("No events triggered this week")

        except Exception as e:
            print_error(f"Error advancing week: {e}")

        input("\nPress Enter to continue...")

    def handle_advance_to_next_event(self):
        """Advance calendar to the next scheduled event date."""
        print_separator()
        print_info("Finding next scheduled event...")

        try:
            current_date = self.controller.calendar.get_current_date()

            # Get upcoming events to find the next one
            upcoming_events = self._get_upcoming_events(limit=1)

            if not upcoming_events:
                print_warning("No more offseason events scheduled")
                input("\nPress Enter to continue...")
                return

            next_event = upcoming_events[0]
            next_event_timestamp = next_event.get('timestamp')

            if next_event_timestamp:
                # Convert timestamp to Date
                target_date = Date(
                    next_event_timestamp.year,
                    next_event_timestamp.month,
                    next_event_timestamp.day
                )

                print(f"\nAdvancing to {target_date}...")

                # Advance day by day until we reach the event
                days_advanced = 0
                all_triggered_events = []

                while self.controller.calendar.get_current_date() < target_date:
                    result = self.controller.advance_day()
                    days_advanced += 1

                    # Collect any events that triggered
                    if result.get('events_triggered'):
                        all_triggered_events.extend(result['events_triggered'])

                # Advance one more day to trigger the target event
                result = self.controller.advance_day()
                days_advanced += 1
                if result.get('events_triggered'):
                    all_triggered_events.extend(result['events_triggered'])

                print(f"\n✅ Advanced {days_advanced} days to {self.controller.calendar.get_current_date()}")

                if all_triggered_events:
                    print(f"\n📅 Events Triggered:")
                    self._display_triggered_events(all_triggered_events)
            else:
                print_warning("Could not determine event date")

        except Exception as e:
            print_error(f"Error advancing to next event: {e}")

        input("\nPress Enter to continue...")

    def handle_view_upcoming_events(self):
        """Display next 10 scheduled offseason events."""
        print_separator()
        print_info("Fetching upcoming events...")

        try:
            current_date = self.controller.calendar.get_current_date()
            events = self._get_upcoming_events(limit=10)

            if not events:
                print_warning("No upcoming events scheduled")
                input("\nPress Enter to continue...")
                return

            print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'='*80}{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}UPCOMING OFFSEASON EVENTS{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'='*80}{Colors.RESET}\n")

            for i, event in enumerate(events, 1):
                event_timestamp = event.get('timestamp')
                event_type = event.get('event_type', 'UNKNOWN')
                data = event.get('data', {})

                # Calculate days until event
                if event_timestamp:
                    event_date = Date(event_timestamp.year, event_timestamp.month, event_timestamp.day)
                    days_until = current_date.days_until(event_date)
                    date_str = f"{event_date} ({days_until} days)"
                else:
                    date_str = "Unknown date"

                # Get description
                description = data.get('description', data.get('deadline_type', event_type))

                print(f"{Colors.BOLD}{i}. {date_str}{Colors.RESET}")
                print(f"   Type: {event_type}")
                print(f"   {description}")
                print()

            print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'='*80}{Colors.RESET}")

        except Exception as e:
            print_error(f"Error retrieving upcoming events: {e}")

        input("\nPress Enter to continue...")

    def handle_view_event_history(self):
        """Display event history (placeholder for future implementation)."""
        print_separator()
        print_info("Event history feature coming soon...")
        input("\nPress Enter to continue...")

    def handle_view_stat_leaders(self):
        """View stat leaders (combines regular season and playoff)."""
        print_separator()
        print_info("Fetching stat leaders...")

        try:
            summary = self.controller.season_summary
            if summary:
                print(f"\n{Colors.BOLD}{Colors.GREEN}═══ STAT LEADERS ═══{Colors.RESET}\n")
                # TODO: Display stat leaders
                print("Stat leaders display coming soon")
            else:
                print_warning("Stats not available")

        except Exception as e:
            print_error(f"Error fetching stats: {e}")

        input("\nPress Enter to continue...")

    def _display_triggered_events(self, events):
        """Display events that triggered."""
        if not events:
            print("  No events triggered")
            return

        for event_data in events:
            event_type = event_data.get('event_type', 'UNKNOWN')
            data = event_data.get('data', {})

            if event_type == 'DEADLINE':
                print(f"  ⏰ DEADLINE: {data.get('description', 'Unknown deadline')}")
                if 'message' in data:
                    print(f"     {data['message']}")

            elif event_type == 'WINDOW':
                window_type = data.get('window_type', 'Unknown')
                action = data.get('action', 'UNKNOWN')
                print(f"  📅 WINDOW: {window_type} {action}")

            elif event_type == 'MILESTONE':
                print(f"  🎯 MILESTONE: {data.get('description', 'Unknown milestone')}")

    def _get_upcoming_events(self, limit=10):
        """
        Get upcoming events from the event database.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries sorted by timestamp
        """
        try:
            current_date = self.controller.calendar.get_current_date()

            # Get all DEADLINE, WINDOW, and MILESTONE events
            all_events = []

            # Query each event type
            for event_type in ['DEADLINE', 'WINDOW', 'MILESTONE']:
                events = self.controller.season_controller.event_db.get_events_by_type(event_type)
                all_events.extend(events)

            # Filter for events after current date
            upcoming = []
            for event in all_events:
                event_timestamp = event.get('timestamp')
                if event_timestamp:
                    event_date = Date(event_timestamp.year, event_timestamp.month, event_timestamp.day)
                    if event_date >= current_date:
                        upcoming.append(event)

            # Sort by timestamp (ascending - earliest first)
            upcoming.sort(key=lambda e: e.get('timestamp'))

            # Return limited results
            return upcoming[:limit]

        except Exception as e:
            self.logger.error(f"Error getting upcoming events: {e}")
            return []

    def handle_view_season_summary(self):
        """View comprehensive season summary."""
        print_separator()
        print_info("Generating season summary...")

        try:
            # Get season summary from controller
            summary = self.controller.season_summary
            if summary:
                print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}═══ SEASON SUMMARY ═══{Colors.RESET}\n")
                print(f"Season Year: {summary.get('season_year')}")
                print(f"Dynasty: {summary.get('dynasty_id')}")
                print(f"Total Games: {summary.get('total_games')}")
                print(f"Total Days: {summary.get('total_days')}")
                # TODO: Display more summary details
            else:
                print_warning("Season summary not available")

        except Exception as e:
            print_error(f"Error fetching summary: {e}")

        input("\nPress Enter to continue...")

    # ========== SHARED UTILITIES ==========

    def display_phase_transition(self, transition_info: dict):
        """
        Display phase transition notification.

        Args:
            transition_info: Dictionary with transition details
        """
        from_phase = transition_info.get('from_phase', 'unknown').replace('_', ' ').title()
        to_phase = transition_info.get('to_phase', 'unknown').replace('_', ' ').title()
        trigger = transition_info.get('trigger', 'unknown')

        print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}{'PHASE TRANSITION'.center(80)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}{'='*80}{Colors.RESET}\n")

        print(f"{Colors.BOLD}From Phase:{Colors.RESET} {from_phase}")
        print(f"{Colors.BOLD}To Phase:{Colors.RESET} {to_phase}")
        print(f"{Colors.BOLD}Trigger:{Colors.RESET} {trigger}")

        print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}{'='*80}{Colors.RESET}\n")

        # Phase-specific messages
        if to_phase == "Playoffs":
            print_success("🏆 Regular Season Complete - Playoffs Starting!")
            print_info("Playoff bracket has been generated from final standings")
        elif to_phase == "Offseason":
            print_success("🏆 Super Bowl Complete - Season Finished!")
            print_info("View season summary and stat leaders from the offseason menu")

    def handle_exit(self):
        """Exit the simulator."""
        print_separator()
        print_info("Exiting Interactive Full Season Simulator")

        # Get final state
        try:
            state = self.controller.get_current_state()
            current_phase = self.controller.get_current_phase()

            print(f"\nFinal Status:")
            print(f"  Dynasty: {self.dynasty_id}")
            print(f"  Total Games Played: {state['total_games_played']} / 285")
            print(f"  Current Phase: {current_phase.value.replace('_', ' ').title()}")
            print(f"  Days Simulated: {state['total_days_simulated']}")
        except:
            pass

        print_success("Thanks for using the simulator!")
        self.running = False


def main():
    """Main entry point."""
    try:
        # Prompt for dynasty name
        print_banner()
        print_info("Welcome to the Interactive NFL Full Season Simulator!")
        print_separator()
        print("\nThis simulator will guide you through a complete NFL season:")
        print("  • Regular Season (272 games, 18 weeks)")
        print("  • Playoffs (13 games: Wild Card → Super Bowl)")
        print("  • Offseason (summary and stat viewing)")
        print("\nEach simulation requires a unique dynasty name for data isolation.")
        print("You can provide a custom name or use an auto-generated one.\n")

        dynasty_name = input("Enter dynasty name (or press Enter for auto-generated): ").strip()

        # Generate dynasty ID
        if dynasty_name:
            # User provided a name - use it directly
            dynasty_id = dynasty_name
            print_success(f"Using dynasty: {dynasty_id}")
        else:
            # Auto-generate timestamp-based dynasty ID
            dynasty_id = f"dynasty_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print_info(f"Auto-generated dynasty: {dynasty_id}")

        print()

        # Initialize simulator with unique dynasty ID
        simulator = InteractiveFullSeasonSimulator(dynasty_id=dynasty_id)
        simulator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
