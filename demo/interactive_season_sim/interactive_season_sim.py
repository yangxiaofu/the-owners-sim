#!/usr/bin/env python3
"""
Interactive Season Simulator

Terminal-based interactive NFL season simulation with day/week/full season control.

Commands:
  [1] Advance 1 day
  [2] Advance 7 days (1 week)
  [3] Simulate to end of season
  [4] Show current standings
  [5] Show upcoming games
  [6] Show season summary
  [0] Exit
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from calendar.date_models import Date

# Handle both direct execution and module import
try:
    from .season_controller import SeasonController
    from .display_utils import *
except ImportError:
    # Direct execution - use absolute imports
    from season_controller import SeasonController
    from display_utils import *


class InteractiveSeasonSimulator:
    """
    Interactive terminal interface for season simulation.

    Provides user control over simulation pace:
    - Day-by-day advancement
    - Week-by-week advancement
    - Simulate to end of season
    - View standings and upcoming games
    """

    def __init__(
        self,
        dynasty_id: str,
        database_path: str = None
    ):
        """
        Initialize interactive season simulator.

        Args:
            dynasty_id: Unique dynasty identifier for data isolation
            database_path: Path to season database (defaults to data/season_2024.db relative to this script)
        """
        print_info("Initializing Interactive Season Simulator...")

        # Use absolute path for database to avoid duplicate databases when running from different directories
        if database_path is None:
            database_path = str(Path(__file__).parent / "data" / "season_2024.db")

        # Store dynasty ID
        self.dynasty_id = dynasty_id

        # Create season controller
        try:
            self.controller = SeasonController(
                database_path=database_path,
                start_date=Date(2024, 9, 5),  # September 5, 2024 (Thursday)
                season_year=2024,
                dynasty_id=dynasty_id
            )
            print_success("Season controller initialized successfully")
        except Exception as e:
            print_error(f"Failed to initialize controller: {e}")
            raise

        self.running = True
        self.database_path = database_path

    def run(self):
        """Main terminal loop."""
        clear_screen()
        print_banner()

        print_success("Welcome to the Interactive NFL Season Simulator!")
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

            # Display menu
            print_menu()

            # Get user input
            try:
                choice = input("\n" + Colors.BRIGHT_CYAN + "Enter command: " + Colors.RESET).strip()

                # Handle command
                self.handle_command(choice)

            except KeyboardInterrupt:
                print("\n")
                self.handle_exit()
                break
            except Exception as e:
                print_error(f"Error processing command: {e}")
                input("\nPress Enter to continue...")

    def display_current_status(self):
        """Display current season status."""
        # Display dynasty info
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}🏆 Dynasty: {self.dynasty_id}{Colors.RESET}")

        # Display simulation status
        state = self.controller.get_current_state()
        print_status(state)

    def handle_command(self, choice: str):
        """
        Handle user command.

        Args:
            choice: User's menu choice
        """
        if choice == "1":
            self.handle_advance_day()
        elif choice == "2":
            self.handle_advance_week()
        elif choice == "3":
            self.handle_simulate_to_end()
        elif choice == "4":
            self.handle_show_standings()
        elif choice == "5":
            self.handle_show_upcoming()
        elif choice == "6":
            self.handle_show_summary()
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

            if result['success']:
                # Display results
                display_daily_results(result)

                # Show phase transitions if any
                if result.get('phase_transitions'):
                    for transition in result['phase_transitions']:
                        print_success(f"🔄 Phase Transition: {transition['from_phase']} → {transition['to_phase']}")
            else:
                print_error("Failed to advance day")
                for error in result.get('errors', []):
                    print_error(f"  {error}")

        except Exception as e:
            print_error(f"Error advancing day: {e}")

        input("\nPress Enter to continue...")

    def handle_advance_week(self):
        """Advance 7 days and display weekly summary."""
        print_separator()
        print_info("Advancing 7 days (1 week)...")

        try:
            result = self.controller.advance_week()

            if result['success']:
                display_weekly_summary(result)
            else:
                print_error("Failed to advance week")

        except Exception as e:
            print_error(f"Error advancing week: {e}")

        input("\nPress Enter to continue...")

    def handle_simulate_to_end(self):
        """Simulate to end of regular season."""
        print_separator()
        print_warning("⚠️  This will simulate the entire remaining season.")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm != 'y':
            print_info("Simulation cancelled")
            input("\nPress Enter to continue...")
            return

        print_separator()
        print_info("Simulating to end of season...")
        print_info("This may take several minutes...")
        print()

        try:
            result = self.controller.simulate_to_end()

            if result['success']:
                print()
                display_season_summary(result)
            else:
                print_error("Failed to simulate season")

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
            games = self.controller.get_upcoming_games(days=days)
            display_upcoming_games(games, days=days)

        except Exception as e:
            print_error(f"Error fetching upcoming games: {e}")

        input("\nPress Enter to continue...")

    def handle_show_summary(self):
        """Display current season summary."""
        print_separator()
        print_info("Season Summary")
        print_separator()

        try:
            state = self.controller.get_current_state()

            print(f"\n{Colors.BOLD}Current Season Status{Colors.RESET}")
            print(f"  Season Year: {state['season_year']}")
            print(f"  Current Date: {state['current_date']}")
            print(f"  Week: {state['week_number']} of 18")
            print(f"  Games Played: {state['games_played']} of 272")
            print(f"  Days Simulated: {state['days_simulated']}")
            print(f"  Current Phase: {state['current_phase']}")

            # Progress bar
            progress = progress_bar(state['games_played'], 272, width=50, label="Season Progress")
            print(f"\n{progress}")

            # Phase info
            phase_info = state.get('phase_info', {})
            if phase_info:
                print(f"\n{Colors.BOLD}Phase Information{Colors.RESET}")
                print(f"  Regular Season Games: {phase_info.get('completed_regular_season_games', 0)} / 272")
                print(f"  Completion: {phase_info.get('regular_season_completion_percentage', 0):.1f}%")
                print(f"  Days in Phase: {phase_info.get('days_in_current_phase', 0)}")

        except Exception as e:
            print_error(f"Error fetching summary: {e}")

        input("\nPress Enter to continue...")

    def handle_exit(self):
        """Exit the simulator."""
        print_separator()
        print_info("Exiting Interactive Season Simulator")

        # Get final state
        try:
            state = self.controller.get_current_state()
            print(f"\nFinal Status:")
            print(f"  Dynasty: {self.dynasty_id}")
            print(f"  Games Played: {state['games_played']} of 272")
            print(f"  Current Week: {state['week_number']}")
            print(f"  Current Phase: {state['current_phase']}")
        except:
            pass

        print_success("Thanks for using the simulator!")
        self.running = False


def main():
    """Main entry point."""
    try:
        from datetime import datetime

        # Prompt for dynasty name
        print_banner()
        print_info("Welcome to the Interactive NFL Season Simulator!")
        print_separator()
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
        simulator = InteractiveSeasonSimulator(dynasty_id=dynasty_id)
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
