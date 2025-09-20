"""
Interactive Interface

Main interface component for the terminal-based NFL season simulation demo.
Handles user interaction, menu display, and coordinates between the simulation
controller and display formatter.
"""

import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime

from demo.weekly_simulation_controller import WeeklySimulationController
from demo.daily_simulation_controller import DailySimulationController
from demo.results_display_formatter import ResultsDisplayFormatter


class InteractiveInterface:
    """
    Main interactive terminal interface for the NFL season simulation demo.
    
    Provides a menu-driven interface that allows users to:
    - Initialize new seasons
    - Simulate weeks one at a time
    - View current standings
    - View season progress
    - Navigate through the simulation
    """
    
    def __init__(self):
        """Initialize the interactive interface."""
        self.weekly_controller = WeeklySimulationController()
        self.daily_controller = DailySimulationController()
        self.formatter = ResultsDisplayFormatter()
        self.running = True
        
        # Simulation mode: 'weekly' or 'daily'
        self.simulation_mode = 'weekly'  # Default to weekly for backward compatibility
        
        # Demo state
        self.last_week_results: Optional[Dict[str, Any]] = None
        self.last_day_results: Optional[Dict[str, Any]] = None
        
    @property
    def controller(self):
        """Get the current active controller based on simulation mode."""
        return self.daily_controller if self.simulation_mode == 'daily' else self.weekly_controller
        
    def run(self):
        """Main demo loop."""
        self._display_welcome()
        
        # Initialize season first
        if not self._initialize_season_interactive():
            print(self.formatter.format_error("Failed to initialize season. Exiting."))
            return
        
        # Main interaction loop
        while self.running:
            try:
                self._display_main_menu()
                choice = self._get_user_input()
                self._handle_menu_choice(choice)
                
            except KeyboardInterrupt:
                self._handle_exit()
                break
            except Exception as e:
                print(self.formatter.format_error(f"Unexpected error: {e}"))
                print("Press Enter to continue...")
                input()
    
    def _display_welcome(self):
        """Display welcome screen and introduction."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("🏈 NFL SEASON SIMULATION DEMO"))
        print()
        print("Welcome to the interactive NFL season simulator!")
        print("Experience the thrill of managing a complete NFL season.")
        print()
        print("🗓️ SIMULATION MODES:")
        print("  📅 Daily Mode: Simulate day-by-day with detailed control")
        print("  📆 Weekly Mode: Simulate week-by-week for faster progression")
        print()
        print(self.formatter.format_info("Let's get started by setting up your season..."))
        print()
        input("Press Enter to continue...")
    
    def _initialize_season_interactive(self) -> bool:
        """Interactive season initialization."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SEASON SETUP"))
        print()
        
        # Get simulation mode
        print("🗓️ SIMULATION MODE:")
        print("  1. Daily Mode - Day-by-day simulation with detailed control")
        print("  2. Weekly Mode - Week-by-week simulation for faster progression")
        print()
        print("Choose simulation mode (1-2, default: 2): ", end="")
        mode_input = input().strip()
        
        if mode_input == '1':
            self.simulation_mode = 'daily'
            print(self.formatter.format_info("📅 Daily simulation mode selected"))
        else:
            self.simulation_mode = 'weekly'
            print(self.formatter.format_info("📆 Weekly simulation mode selected"))
        
        print()
        
        # Get season year
        current_year = datetime.now().year
        print(f"Season Year (default: {current_year}): ", end="")
        year_input = input().strip()
        season_year = int(year_input) if year_input.isdigit() else current_year
        
        # Get dynasty name
        print("Dynasty Name (default: 'My Dynasty'): ", end="")
        dynasty_input = input().strip()
        dynasty_name = dynasty_input if dynasty_input else "My Dynasty"
        
        print()
        print(self.formatter.format_info(f"Initializing {season_year} season: '{dynasty_name}'..."))
        print(f"Mode: {self.simulation_mode.title()} simulation")
        print("This may take a moment...")
        
        # Initialize the season for both controllers to keep them in sync
        weekly_result = self.weekly_controller.initialize_season(season_year, dynasty_name)
        daily_result = self.daily_controller.initialize_season(season_year, dynasty_name)
        
        # Use the result from the active controller
        result = daily_result if self.simulation_mode == 'daily' else weekly_result
        
        if result['success']:
            print()
            print(self.formatter.format_success("Season initialized successfully!"))
            print(f"Dynasty: {dynasty_name}")
            print(f"Season: {season_year}")
            print(f"Mode: {self.simulation_mode.title()} simulation")
            if 'total_games' in result:
                print(f"Total Games: {result['total_games']}")
            if 'season_start' in result:
                print(f"Season Dates: {result['season_start']} to {result['season_end']}")
            print()
            input("Press Enter to begin the season...")
            return True
        else:
            print()
            print(self.formatter.format_error(f"Initialization failed: {result.get('error', 'Unknown error')}"))
            print()
            input("Press Enter to continue...")
            return False
    
    def _display_main_menu(self):
        """Display the main menu."""
        print(self.formatter.clear_screen())
        
        # Season status
        status = self.controller.get_season_status()
        print(self.formatter.format_season_status(status))
        
        # Display mode indicator
        mode_icon = "📅" if self.simulation_mode == "daily" else "📆"
        print(f"{mode_icon} Mode: {self.simulation_mode.title()} Simulation")
        print()
        
        # Last results (daily or weekly)
        if self.simulation_mode == 'daily' and self.last_day_results:
            print("📅 Last Day Results:")
            day_result = self.last_day_results
            print(f"  Date: {day_result.get('date', 'Unknown')}")
            print(f"  Games: {day_result.get('events_executed', 0)}")
            if day_result.get('successful_events', 0) > 0:
                print(f"  Successful: {day_result.get('successful_events', 0)}")
            if day_result.get('errors'):
                print(f"  Errors: {len(day_result.get('errors', []))}")
            print()
        elif self.simulation_mode == 'weekly' and self.last_week_results:
            print(self.formatter.format_week_results(self.last_week_results))
        
        # Menu options based on simulation mode
        options = []
        
        if self.simulation_mode == 'daily':
            # Daily simulation options
            if not status.get('season_complete', False):
                options.extend([
                    "Simulate Next Day",
                    "Simulate Next Game Day", 
                    "Simulate Next 7 Days",
                    "Switch to Weekly Mode"
                ])
        else:
            # Weekly simulation options  
            if not status.get('season_complete', False):
                options.extend([
                    "Simulate Next Week",
                    "Switch to Daily Mode"
                ])
        
        # Common options for both modes
        options.extend([
            "View Current Standings",
            "View Leaderboards",
            "View Season Progress",
            "Help",
            "Exit"
        ])
        
        if status.get('season_complete', False):
            options.insert(-2, "View Final Standings")
        
        menu_text = self.formatter.format_menu(options, "What would you like to do?")
        print(menu_text, end="")
    
    def _get_user_input(self) -> str:
        """Get and validate user input."""
        while True:
            try:
                choice = input().strip().lower()
                if choice:
                    return choice
                print("Please enter a valid choice: ", end="")
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt()
    
    def _handle_menu_choice(self, choice: str):
        """Handle user menu selection."""
        status = self.controller.get_season_status()
        
        # Handle simulation mode specific choices
        if self.simulation_mode == 'daily' and not status.get('season_complete', False):
            if choice in ['1', 'day', 'next']:
                self._simulate_next_day()
                return
            elif choice in ['2', 'game', 'gameday']:
                self._simulate_next_game_day()
                return
            elif choice in ['3', '7', 'week', '7days']:
                self._simulate_next_7_days()
                return
            elif choice in ['4', 'switch', 'weekly']:
                self._switch_to_weekly_mode()
                return
                
        elif self.simulation_mode == 'weekly' and not status.get('season_complete', False):
            if choice in ['1', 'simulate', 'sim', 'next', 'week']:
                self._simulate_next_week()
                return
            elif choice in ['2', 'switch', 'daily']:
                self._switch_to_daily_mode()
                return
        
        # Handle common choices (adjust numbers based on mode and season status)
        common_offset = 4 if self.simulation_mode == 'daily' else 2
        if status.get('season_complete', False):
            common_offset -= 1  # Adjust for missing simulation options when complete
            
        # Map common choices
        standings_choice = str(common_offset + 1) if not status.get('season_complete', False) else '1'
        leaderboards_choice = str(common_offset + 2) if not status.get('season_complete', False) else '2'
        progress_choice = str(common_offset + 3) if not status.get('season_complete', False) else '3'
        help_choice = str(common_offset + 4) if not status.get('season_complete', False) else '4'
        exit_choice = str(common_offset + 5) if not status.get('season_complete', False) else '5'

        if choice in [standings_choice, 'standings', 'stand']:
            self._view_standings()
        elif choice in [leaderboards_choice, 'leaderboards', 'leaders', 'stats']:
            self._view_leaderboards()
        elif choice in [progress_choice, 'progress', 'status', 'prog']:
            self._view_season_progress()
        elif choice in [help_choice, 'help']:
            self._show_help()
        elif choice in [exit_choice, 'exit', 'quit', 'q']:
            self._handle_exit()
        else:
            print(self.formatter.format_error("Invalid choice. Please try again."))
            input("Press Enter to continue...")
    
    def _simulate_next_week(self):
        """Simulate the next week of the season."""
        print(self.formatter.clear_screen())
        
        status = self.controller.get_season_status()
        next_week = status['current_week'] + 1
        
        print(self.formatter.format_header(f"SIMULATING WEEK {next_week}"))
        print()
        print(self.formatter.format_info(f"Running simulation for Week {next_week}..."))
        print("🎮 Simulating games...")
        
        # Simulate with a brief delay for effect
        time.sleep(1)
        
        try:
            week_results = self.controller.simulate_next_week()
            self.last_week_results = week_results.__dict__ if hasattr(week_results, '__dict__') else {
                'week_number': week_results.week_number,
                'game_results': week_results.game_results,
                'successful_games': week_results.successful_games,
                'failed_games': week_results.failed_games,
                'errors': week_results.errors
            }
            
            print()
            print(self.formatter.format_success(f"Week {next_week} simulation complete!"))
            
            # Brief pause before showing results
            time.sleep(0.5)
            
        except Exception as e:
            print()
            print(self.formatter.format_error(f"Simulation failed: {str(e)}"))
            input("Press Enter to continue...")
    
    def _simulate_next_day(self):
        """Simulate the next day in the season."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SIMULATING NEXT DAY"))
        print()
        
        try:
            # Get current date info
            if hasattr(self.daily_controller, 'current_date') and self.daily_controller.current_date:
                current_date = self.daily_controller.current_date
                day_info = self.daily_controller.get_day_info(current_date)
                
                print(f"📅 Date: {current_date.strftime('%A, %B %d, %Y')}")
                print(f"🏈 Games scheduled: {day_info.games_scheduled}")
                print()
                
                if day_info.games_scheduled > 0:
                    print(self.formatter.format_info("Simulating games..."))
                else:
                    print(self.formatter.format_info("No games scheduled, advancing date..."))
                
                time.sleep(1)
                
                # Simulate the day
                day_result = self.daily_controller.simulate_next_day()
                
                # Store results for display
                self.last_day_results = {
                    'date': current_date.strftime('%A, %B %d, %Y'),
                    'events_executed': day_result.events_executed,
                    'successful_events': day_result.successful_events,
                    'failed_events': day_result.failed_events,
                    'errors': day_result.errors
                }
                
                print()
                if day_result.events_executed > 0:
                    print(self.formatter.format_success(f"Day complete! {day_result.successful_events} games simulated"))
                else:
                    print(self.formatter.format_success("Day advanced (no games scheduled)"))
                
                if day_result.errors:
                    print(f"⚠️ {len(day_result.errors)} errors occurred")
                
                time.sleep(0.5)
                
            else:
                print(self.formatter.format_error("No current date set"))
                input("Press Enter to continue...")
                
        except Exception as e:
            print()
            print(self.formatter.format_error(f"Daily simulation failed: {str(e)}"))
            input("Press Enter to continue...")
    
    def _simulate_next_game_day(self):
        """Find and simulate the next day with games."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SIMULATING NEXT GAME DAY"))
        print()
        
        try:
            print(self.formatter.format_info("Finding next day with games..."))
            
            # Find and simulate next game day
            day_result, days_skipped = self.daily_controller.simulate_next_game_day()
            
            # Store results for display
            self.last_day_results = {
                'date': day_result.date.strftime('%A, %B %d, %Y'),
                'events_executed': day_result.events_executed,
                'successful_events': day_result.successful_events,
                'failed_events': day_result.failed_events,
                'errors': day_result.errors
            }
            
            print()
            if days_skipped > 0:
                print(f"📅 Skipped {days_skipped} non-game days")
            
            print(self.formatter.format_success(f"Game day complete! {day_result.successful_events} games simulated"))
            print(f"📅 Date: {day_result.date.strftime('%A, %B %d, %Y')}")
            
            if day_result.errors:
                print(f"⚠️ {len(day_result.errors)} errors occurred")
            
            time.sleep(0.5)
            
        except Exception as e:
            print()
            print(self.formatter.format_error(f"Game day simulation failed: {str(e)}"))
            input("Press Enter to continue...")
    
    def _simulate_next_7_days(self):
        """Simulate the next 7 days."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SIMULATING NEXT 7 DAYS"))
        print()
        
        try:
            print(self.formatter.format_info("Simulating 7 days..."))
            print("This may take a moment...")
            time.sleep(1)
            
            # Simulate 7 days
            multi_day_result = self.daily_controller.simulate_next_7_days()
            
            print()
            print(self.formatter.format_success("7-day simulation complete!"))
            print(f"📅 Period: {multi_day_result.start_date} to {multi_day_result.end_date}")
            print(f"🏈 Total games: {multi_day_result.total_games}")
            print(f"✅ Successful: {multi_day_result.total_successful}")
            
            if multi_day_result.total_failed > 0:
                print(f"❌ Failed: {multi_day_result.total_failed}")
            
            if multi_day_result.errors:
                print(f"⚠️ {len(multi_day_result.errors)} total errors")
            
            # Store summary for display
            self.last_day_results = {
                'date': f"{multi_day_result.start_date} to {multi_day_result.end_date}",
                'events_executed': multi_day_result.total_games,
                'successful_events': multi_day_result.total_successful,
                'failed_events': multi_day_result.total_failed,
                'errors': multi_day_result.errors
            }
            
            time.sleep(0.5)
            
        except Exception as e:
            print()
            print(self.formatter.format_error(f"7-day simulation failed: {str(e)}"))
            input("Press Enter to continue...")
    
    def _switch_to_weekly_mode(self):
        """Switch from daily to weekly simulation mode."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SWITCHING TO WEEKLY MODE"))
        print()
        
        print("📆 Switching to weekly simulation mode...")
        self.simulation_mode = 'weekly'
        self.last_day_results = None  # Clear daily results
        
        print(self.formatter.format_success("Now in weekly simulation mode"))
        print("You can now simulate entire weeks at once.")
        print()
        input("Press Enter to continue...")
    
    def _switch_to_daily_mode(self):
        """Switch from weekly to daily simulation mode."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SWITCHING TO DAILY MODE"))
        print()
        
        print("📅 Switching to daily simulation mode...")
        self.simulation_mode = 'daily'
        self.last_week_results = None  # Clear weekly results
        
        print(self.formatter.format_success("Now in daily simulation mode"))
        print("You can now simulate individual days with detailed control.")
        print()
        input("Press Enter to continue...")
    
    def _view_standings(self):
        """Display current standings."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("CURRENT STANDINGS"))
        
        standings = self.controller.get_current_standings()
        standings_display = self.formatter.format_standings(standings)
        print(standings_display)
        
        input("Press Enter to return to main menu...")
    
    def _view_season_progress(self):
        """Display detailed season progress."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SEASON PROGRESS"))
        
        status = self.controller.get_season_status()
        progress_display = self.formatter.format_season_status(status)
        print(progress_display)
        
        # Additional progress details
        print(self.formatter.format_info("Season Timeline:"))
        if status['season_start_date']:
            print(f"  Start Date: {status['season_start_date']}")
        if status['season_end_date']:
            print(f"  End Date: {status['season_end_date']}")
        
        print()
        print(f"  Current Week: {status['current_week']} of 18")
        print(f"  Weeks Remaining: {status['weeks_remaining']}")
        
        if status['season_complete']:
            print()
            print(self.formatter.format_success("🏆 Congratulations! Season completed!"))
            print("You can view final standings and review your dynasty's performance.")
        
        print()
        input("Press Enter to return to main menu...")
    
    def _show_help(self):
        """Display help information."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("HELP & INSTRUCTIONS"))
        print()
        
        print(self.formatter.format_info("How to Use the NFL Season Simulator:"))
        print()
        
        print("📋 MENU OPTIONS:")
        print("  1. Simulate Next Week - Run the next week's games")
        print("  2. View Standings - See current division and conference standings")
        print("  3. Season Progress - View detailed season progress and timeline")
        print("  4. Help - Show this help screen")
        print("  5. Exit - Quit the simulator")
        print()
        
        print("🎮 SIMULATION FEATURES:")
        print("  • Week-by-week progression through 18-week NFL season")
        print("  • Realistic game simulation with scores and outcomes")
        print("  • Live standings tracking by division and conference")
        print("  • Complete season statistics and progress tracking")
        print("  • Colorized terminal output for better readability")
        print()
        
        print("💡 TIPS:")
        print("  • You can type full command names (e.g., 'simulate', 'standings')")
        print("  • Short versions work too (e.g., '1', 'sim', 'stand')")
        print("  • Use Ctrl+C at any time to exit the simulator")
        print("  • Each week shows all game results with winners and scores")
        print()
        
        print("🏆 SEASON COMPLETION:")
        print("  • Complete all 18 weeks to finish your season")
        print("  • Final standings determine playoff seeding")
        print("  • Review your dynasty's performance throughout the season")
        print()
        
        input("Press Enter to return to main menu...")
    
    def _handle_exit(self):
        """Handle exit confirmation and cleanup."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("EXIT CONFIRMATION"))
        print()
        
        status = self.controller.get_season_status()
        if status['season_initialized'] and not status['season_complete']:
            print(self.formatter.format_warning("Your season is not yet complete."))
            print(f"Current progress: Week {status['current_week']} of 18")
            print()
            print("Are you sure you want to exit? (y/N): ", end="")
            
            confirm = input().strip().lower()
            if confirm not in ['y', 'yes']:
                print()
                print(self.formatter.format_info("Returning to main menu..."))
                time.sleep(1)
                return
        
        # Final exit message
        print()
        print(self.formatter.format_success("Thank you for playing!"))
        if status['season_initialized']:
            print(f"Dynasty '{status['dynasty_name']}' - {status['season_year']} Season")
            print(f"Final Progress: {status['progress_percentage']:.1f}% complete")
        
        print()
        print("🏈 Come back anytime to simulate more NFL seasons!")
        print()

        self.running = False

    def _view_leaderboards(self):
        """Display leaderboards submenu and handle selection."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SEASON LEADERBOARDS"))

        # Leaderboard options
        leaderboard_options = [
            "Passing Leaders",
            "Rushing Leaders",
            "Receiving Leaders",
            "Return to Main Menu"
        ]

        menu_text = self.formatter.format_menu(leaderboard_options, "Select a leaderboard:")
        print(menu_text, end="")

        choice = self._get_user_input()

        # Handle leaderboard choice
        if choice in ['1', 'passing', 'pass']:
            self._view_passing_leaders()
        elif choice in ['2', 'rushing', 'rush']:
            self._view_rushing_leaders()
        elif choice in ['3', 'receiving', 'rec']:
            self._view_receiving_leaders()
        elif choice in ['4', 'return', 'back', 'main']:
            return  # Return to main menu
        else:
            print(self.formatter.format_error("Invalid choice. Please try again."))
            input("Press Enter to continue...")
            self._view_leaderboards()  # Show menu again

    def _view_passing_leaders(self):
        """Display passing leaders leaderboard."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("PASSING LEADERS"))

        try:
            # Get passing leaders from database
            leaders = self.controller.database_api.get_passing_leaders(
                self.controller.dynasty_id,
                self.controller.season_year,
                limit=15
            )

            # Format and display
            leaderboard_display = self.formatter.format_passing_leaders(leaders)
            print(leaderboard_display)

        except Exception as e:
            print(self.formatter.format_error(f"Could not retrieve passing leaders: {str(e)}"))
            print()

        input("Press Enter to return to leaderboards menu...")

    def _view_rushing_leaders(self):
        """Display rushing leaders leaderboard."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("RUSHING LEADERS"))

        try:
            # Get rushing leaders from database
            leaders = self.controller.database_api.get_rushing_leaders(
                self.controller.dynasty_id,
                self.controller.season_year,
                limit=15
            )

            # Format and display
            leaderboard_display = self.formatter.format_rushing_leaders(leaders)
            print(leaderboard_display)

        except Exception as e:
            print(self.formatter.format_error(f"Could not retrieve rushing leaders: {str(e)}"))
            print()

        input("Press Enter to return to leaderboards menu...")

    def _view_receiving_leaders(self):
        """Display receiving leaders leaderboard."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("RECEIVING LEADERS"))

        try:
            # Get receiving leaders from database
            leaders = self.controller.database_api.get_receiving_leaders(
                self.controller.dynasty_id,
                self.controller.season_year,
                limit=15
            )

            # Format and display
            leaderboard_display = self.formatter.format_receiving_leaders(leaders)
            print(leaderboard_display)

        except Exception as e:
            print(self.formatter.format_error(f"Could not retrieve receiving leaders: {str(e)}"))
            print()

        input("Press Enter to return to leaderboards menu...")