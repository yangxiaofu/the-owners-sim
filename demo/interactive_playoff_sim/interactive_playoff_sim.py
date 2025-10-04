#!/usr/bin/env python3
"""
Interactive Playoff Simulator

Terminal-based interactive NFL playoff simulation with day/week/round control.

Commands:
  [1] Advance 1 day
  [2] Advance 7 days (1 week)
  [3] Complete current playoff round (ONLY current round, not next)
  [4] Show current bracket
  [5] Show completed games
  [6] Simulate to Super Bowl
  [0] Exit

Note: Option [3] completes the CURRENT round only. When done, the next round is
scheduled but NOT simulated. Call [3] again to simulate the next round.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from calendar.date_models import Date

# Import playoff controller from centralized location
from playoff_system.playoff_controller import PlayoffController

# Handle both direct execution and module import for display_utils
try:
    from .display_utils import *
except ImportError:
    # Direct execution - use absolute imports
    from display_utils import *


class InteractivePlayoffSimulator:
    """
    Interactive terminal interface for playoff simulation.

    Provides user control over simulation pace:
    - Day-by-day advancement
    - Week-by-week advancement
    - Round-by-round advancement
    - Simulate to Super Bowl
    - View bracket and completed games
    """

    def __init__(
        self,
        dynasty_id: str,
        database_path: str = None,
        season_year: int = 2024
    ):
        """
        Initialize interactive playoff simulator.

        Args:
            dynasty_id: Unique dynasty identifier for data isolation
            database_path: Path to playoff database (defaults to data/playoffs_2024.db relative to this script)
            season_year: NFL season year (default: 2024)
        """
        print_info("Initializing Interactive Playoff Simulator...")

        # Use absolute path for database to avoid duplicate databases when running from different directories
        if database_path is None:
            database_path = str(Path(__file__).parent / "data" / f"playoffs_{season_year}.db")

        # Store dynasty ID and season
        self.dynasty_id = dynasty_id
        self.season_year = season_year

        # Create playoff controller
        try:
            self.controller = PlayoffController(
                database_path=database_path,
                dynasty_id=dynasty_id,
                season_year=season_year
            )
            print_success("Playoff controller initialized successfully")
        except Exception as e:
            print_error(f"Failed to initialize controller: {e}")
            raise

        self.running = True
        self.database_path = database_path

    def run(self):
        """Main terminal loop."""
        clear_screen()
        print_banner()

        print_success("Welcome to the Interactive NFL Playoff Simulator!")
        print_info(f"Database: {self.database_path}")
        print_info(f"Season: {self.season_year}")
        print_separator()

        # Display initial playoff bracket
        print_info("\n📋 Initial Playoff Bracket Generated\n")
        initial_bracket = self.controller.get_current_bracket()

        if initial_bracket.get('wild_card'):
            display_playoff_bracket(
                initial_bracket['wild_card'],
                self.controller.original_seeding
            )

        input("\nPress Enter to begin simulation...")

        while self.running:
            clear_screen()
            print_banner()

            # Display current status
            try:
                self.display_current_status()
            except Exception as e:
                print_error(f"Error displaying status: {e}")

            # Get current round for menu display
            try:
                state = self.controller.get_current_state()
                # Use active_round for accurate display
                current_round = state.get('active_round', state.get('current_round', 'wild_card'))
            except:
                current_round = 'wild_card'

            # Display menu with current round
            display_playoff_menu(current_round=current_round)

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
        """Display current playoff status."""
        # Display dynasty info
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}🏆 Dynasty: {self.dynasty_id}{Colors.RESET}")
        print(f"{Colors.BOLD}Season: {self.season_year} Playoffs{Colors.RESET}")

        # Display simulation status
        print_status(self.controller)

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
            self.handle_advance_to_next_round()
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

    def handle_advance_day(self):
        """Advance 1 day and display results."""
        print_separator()
        print_info("Advancing 1 day...")

        try:
            result = self.controller.advance_day()

            if result['success']:
                # Display results
                if result['games_played'] > 0:
                    print_success(f"\n✓ {result['games_played']} game(s) simulated")
                    display_playoff_game_results(result['results'])
                else:
                    print_info("No games scheduled for this day")

                # Show round completion if applicable
                if result.get('round_completed'):
                    print_success(f"\n🎉 {result['round_name'].replace('_', ' ').title()} Round Complete!")

                    # Show next round scheduled
                    if result.get('next_round_scheduled'):
                        print_info(f"✓ {result['next_round_name'].replace('_', ' ').title()} Round scheduled")
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
                print_success(f"\n✓ Week advanced successfully")
                print_info(f"Games played: {result['total_games_played']}")

                # Display completed rounds
                if result.get('rounds_completed'):
                    for round_name in result.get('rounds_completed', []):
                        print_success(f"  ✓ {round_name.replace('_', ' ').title()} Round Complete")

                # Show game results
                if result['total_games_played'] > 0:
                    # Collect all games from daily results
                    all_games = []
                    for day_result in result.get('daily_results', []):
                        all_games.extend(day_result.get('results', []))

                    if all_games:
                        display_playoff_game_results(all_games)
            else:
                print_error("Failed to advance week")

        except Exception as e:
            print_error(f"Error advancing week: {e}")

        input("\nPress Enter to continue...")

    def handle_advance_to_next_round(self):
        """Advance until next round completes."""
        print_separator()

        state = self.controller.get_current_state()
        current_round = state.get('current_round', 'wild_card')

        print_info(f"Advancing through {current_round.replace('_', ' ').title()} Round...")

        try:
            result = self.controller.advance_to_next_round()

            if result['success']:
                print_success(f"\n✓ {result['round_name'].replace('_', ' ').title()} Round Complete!")
                print_info(f"Days simulated: {result['days_simulated']}")
                print_info(f"Games played: {result['games_played']}")

                # Display game results
                if result['games_played'] > 0:
                    display_round_summary(result['round_name'], result['results'])

                # Show next round info
                if result.get('next_round_scheduled'):
                    next_round_display = result['next_round'].replace('_', ' ').title()
                    print_separator()
                    print_success(f"\n📋 {next_round_display} Round has been SCHEDULED")
                    print_warning(f"⚠️  But NOT YET SIMULATED!")
                    print_info(f"\n💡 To simulate {next_round_display} Round:")
                    print_info(f"   Select option [3] again to complete {next_round_display}")
                    print_separator()
                elif result['completed_round'] == 'super_bowl':
                    print_success("\n🏆 PLAYOFFS COMPLETE! 🏆")
            else:
                print_error("Failed to advance round")

        except Exception as e:
            print_error(f"Error advancing round: {e}")

        input("\nPress Enter to continue...")

    def handle_show_bracket(self):
        """Display current playoff bracket."""
        print_separator()
        print_info("Current Playoff Bracket")
        print_separator()

        try:
            bracket_data = self.controller.get_current_bracket()
            state = self.controller.get_current_state()
            current_round = state.get('current_round', 'wild_card')

            # Display bracket for current round
            if current_round in bracket_data:
                display_playoff_bracket(
                    bracket_data[current_round],
                    self.controller.original_seeding
                )
            else:
                print_warning("No bracket available for current round")

            # Show playoff progression
            print(f"\n{Colors.BOLD}Playoff Progression:{Colors.RESET}")
            rounds = ['wild_card', 'divisional', 'conference', 'super_bowl']
            for round_name in rounds:
                if round_name in bracket_data:
                    status = "✓ Complete" if round_name != current_round else "▶ In Progress"
                    print(f"  {round_name.replace('_', ' ').title()}: {status}")
                else:
                    print(f"  {round_name.replace('_', ' ').title()}: ⏳ Not Yet Scheduled")

        except Exception as e:
            print_error(f"Error fetching bracket: {e}")

        input("\nPress Enter to continue...")

    def handle_show_completed_games(self):
        """Display all completed playoff games."""
        print_separator()
        print_info("Completed Playoff Games")
        print_separator()

        try:
            # Get all completed games organized by round
            rounds = ['wild_card', 'divisional', 'conference', 'super_bowl']
            total_games = 0

            for round_name in rounds:
                games = self.controller.get_round_games(round_name)
                completed_games = [g for g in games if g.get('success', False)]

                if completed_games:
                    print(f"\n{Colors.BOLD}{round_name.replace('_', ' ').title()} Round ({len(completed_games)} games):{Colors.RESET}")
                    display_playoff_game_results(completed_games)
                    total_games += len(completed_games)

            if total_games == 0:
                print_info("No completed games yet")
            else:
                print(f"\n{Colors.BOLD}Total games completed: {total_games}{Colors.RESET}")

        except Exception as e:
            print_error(f"Error fetching completed games: {e}")

        input("\nPress Enter to continue...")

    def handle_simulate_to_super_bowl(self):
        """Simulate all remaining playoffs to Super Bowl."""
        print_separator()
        print_warning("⚠️  This will simulate all remaining playoff games to the Super Bowl.")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm != 'y':
            print_info("Simulation cancelled")
            input("\nPress Enter to continue...")
            return

        print_separator()
        print_info("Simulating to Super Bowl...")
        print_info("This may take a moment...")
        print()

        try:
            result = self.controller.simulate_to_super_bowl()

            if result['success']:
                print()
                print_success(f"✓ Playoffs complete!")
                print_info(f"Days simulated: {result['days_simulated']}")
                print_info(f"Games played: {result['total_games']}")

                # Display summary by round
                for round_name in ['wild_card', 'divisional', 'conference', 'super_bowl']:
                    games = [g for g in result['all_games'] if g.get('round_name') == round_name]
                    if games:
                        print(f"\n{Colors.BOLD}{round_name.replace('_', ' ').title()} Round:{Colors.RESET}")
                        for game in games:
                            winner_name = game.get('winner_name', 'Unknown')
                            print(f"  ✓ {game['matchup']}: {winner_name} wins")

                # Display Super Bowl winner
                if result.get('super_bowl_result'):
                    print()
                    display_super_bowl_result(result['super_bowl_result'])
            else:
                print_error("Failed to simulate playoffs")

        except Exception as e:
            print_error(f"Error simulating playoffs: {e}")

        input("\nPress Enter to continue...")

    def handle_exit(self):
        """Exit the simulator."""
        print_separator()
        print_info("Exiting Interactive Playoff Simulator")

        # Get final state
        try:
            state = self.controller.get_current_state()
            print(f"\nFinal Status:")
            print(f"  Dynasty: {self.dynasty_id}")
            print(f"  Season: {self.season_year}")
            print(f"  Games Played: {state['games_played']}")
            print(f"  Current Round: {state['current_round'].replace('_', ' ').title()}")
            print(f"  Current Date: {state['current_date']}")
        except:
            pass

        print_success("Thanks for using the playoff simulator!")
        self.running = False


def main():
    """Main entry point."""
    try:
        from datetime import datetime

        # Prompt for dynasty name
        print_banner()
        print_info("Welcome to the Interactive NFL Playoff Simulator!")
        print_separator()
        print("\nEach playoff simulation requires a unique dynasty name for data isolation.")
        print("You can provide a custom name or use an auto-generated one.\n")

        dynasty_name = input("Enter dynasty name (or press Enter for auto-generated): ").strip()

        # Generate dynasty ID
        if dynasty_name:
            # User provided a name - use it directly
            dynasty_id = dynasty_name
            print_success(f"Using dynasty: {dynasty_id}")
        else:
            # Auto-generate timestamp-based dynasty ID
            dynasty_id = f"playoff_dynasty_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print_info(f"Auto-generated dynasty: {dynasty_id}")

        # Ask for season year
        season_input = input("\nEnter season year (or press Enter for 2024): ").strip()
        season_year = int(season_input) if season_input else 2024

        print()

        # Initialize simulator with unique dynasty ID
        simulator = InteractivePlayoffSimulator(
            dynasty_id=dynasty_id,
            season_year=season_year
        )
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
