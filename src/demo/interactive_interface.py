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

# Simulation controllers removed with calendar system
# from demo.weekly_simulation_controller import WeeklySimulationController
# from demo.daily_simulation_controller import DailySimulationController
from demo.results_display_formatter import ResultsDisplayFormatter
from user_team.user_team_manager import UserTeamManager
from team_management.teams.team_loader import TeamDataLoader
from constants.team_ids import TeamIDs


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

        # Team management
        self.team_loader = TeamDataLoader()
        self.user_team_manager: Optional[UserTeamManager] = None
        
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

            # Team selection step
            print(self.formatter.format_info("Now choose your team to manage in this dynasty:"))
            time.sleep(1)

            selected_team_id = self._select_user_team()
            if selected_team_id:
                # Update dynasty with selected team
                update_success = self._update_dynasty_team(selected_team_id)
                if update_success:
                    # Initialize user team manager
                    self._initialize_user_team_manager(selected_team_id)
                    print()
                else:
                    print(self.formatter.format_warning("Dynasty team update failed, but continuing with default team"))
                    print()
            else:
                print(self.formatter.format_warning("No team selected, using default team"))
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

        # Playoff status (if playoffs active)
        if status.get('regular_season_complete', False) or status.get('playoffs_initialized', False):
            self._display_playoff_status(status)
        
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
                    "Simulate Next 7 Days"
                ])

                # Add bulk simulation option if regular season not complete
                if not status.get('regular_season_complete', False):
                    options.append("Simulate to End of Regular Season")

                options.append("Switch to Weekly Mode")
        else:
            # Weekly simulation options
            if not status.get('season_complete', False):
                options.extend([
                    "Simulate Next Week"
                ])

                # Add bulk simulation option if regular season not complete
                if not status.get('regular_season_complete', False):
                    options.append("Simulate to End of Regular Season")

                options.append("Switch to Daily Mode")

        # Add playoff-specific options if playoffs are active
        if status.get('playoffs_initialized', False):
            if self.simulation_mode == 'daily':
                options.insert(-1, "Simulate Playoff Games")  # Insert before "Switch to Weekly Mode"
            else:
                options.insert(-1, "Simulate Playoff Round")  # Insert before "Switch to Daily Mode"
        
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
            elif choice in ['4', 'season', 'end', 'bulk'] and not status.get('regular_season_complete', False):
                self._simulate_to_end_of_regular_season()
                return
            elif choice in ['5', 'playoff', 'playoffs'] and status.get('playoffs_initialized', False):
                self._simulate_playoff_games()
                return
            elif choice in ['4', 'playoff', 'playoffs'] and status.get('playoffs_initialized', False) and status.get('regular_season_complete', False):
                self._simulate_playoff_games()
                return
            elif choice in ['6', 'switch', 'weekly'] and status.get('playoffs_initialized', False):
                self._switch_to_weekly_mode()
                return
            elif choice in ['5', 'switch', 'weekly'] and not status.get('playoffs_initialized', False) and status.get('regular_season_complete', False):
                self._switch_to_weekly_mode()
                return
            elif choice in ['4', 'switch', 'weekly'] and not status.get('playoffs_initialized', False) and not status.get('regular_season_complete', False):
                self._switch_to_weekly_mode()
                return

        elif self.simulation_mode == 'weekly' and not status.get('season_complete', False):
            if choice in ['1', 'simulate', 'sim', 'next', 'week']:
                self._simulate_next_week()
                return
            elif choice in ['2', 'season', 'end', 'bulk'] and not status.get('regular_season_complete', False):
                self._simulate_to_end_of_regular_season()
                return
            elif choice in ['3', 'playoff', 'playoffs'] and status.get('playoffs_initialized', False):
                self._simulate_playoff_round()
                return
            elif choice in ['2', 'playoff', 'playoffs'] and status.get('playoffs_initialized', False) and status.get('regular_season_complete', False):
                self._simulate_playoff_round()
                return
            elif choice in ['4', 'switch', 'daily'] and status.get('playoffs_initialized', False):
                self._switch_to_daily_mode()
                return
            elif choice in ['3', 'switch', 'daily'] and not status.get('playoffs_initialized', False) and status.get('regular_season_complete', False):
                self._switch_to_daily_mode()
                return
            elif choice in ['2', 'switch', 'daily'] and not status.get('playoffs_initialized', False) and not status.get('regular_season_complete', False):
                self._switch_to_daily_mode()
                return
        
        # Handle common choices (adjust numbers based on mode and season status)
        # Calculate offset based on mode and season status
        if self.simulation_mode == 'daily':
            # Daily mode: 3 base options + bulk option (if regular season not complete) + playoff option (if playoffs active) + switch option
            base_offset = 3  # Next Day, Next Game Day, Next 7 Days
            if not status.get('regular_season_complete', False):
                base_offset += 1  # Add bulk simulation option
            if status.get('playoffs_initialized', False):
                base_offset += 1  # Add playoff option
            base_offset += 1  # Switch to Weekly Mode
        else:
            # Weekly mode: 1 base option + bulk option (if regular season not complete) + playoff option (if playoffs active) + switch option
            base_offset = 1  # Next Week
            if not status.get('regular_season_complete', False):
                base_offset += 1  # Add bulk simulation option
            if status.get('playoffs_initialized', False):
                base_offset += 1  # Add playoff option
            base_offset += 1  # Switch to Daily Mode

        common_offset = base_offset
        if status.get('season_complete', False):
            common_offset = 0  # Reset if season is completely done
            
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

    def _simulate_to_end_of_regular_season(self):
        """Simulate all remaining games until the regular season is complete."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SIMULATING TO END OF REGULAR SEASON"))
        print()

        # Check if regular season is already complete
        status = self.controller.get_season_status()
        if status.get('regular_season_complete', False):
            print(self.formatter.format_info("Regular season is already complete!"))
            print()
            input("Press Enter to continue...")
            return

        # Show current progress
        current_week = status.get('current_week', 0)
        print(f"📅 Current Status: Week {current_week} of 18")
        print(f"🎯 Target: Simulate through Week 18 to reach playoffs")
        print()

        # Confirm with user
        print("This will simulate all remaining regular season games.")
        print("This may take several moments depending on how many weeks remain.")
        print()
        confirm = input("Continue? (Y/n): ").strip().lower()

        if confirm not in ['', 'y', 'yes']:
            print()
            print(self.formatter.format_info("Simulation cancelled."))
            input("Press Enter to continue...")
            return

        print()
        print(self.formatter.format_info("Starting bulk simulation to end of regular season..."))
        print("⏳ This may take a moment...")
        time.sleep(1)

        try:
            # Track progress
            start_week = current_week

            # Run the bulk simulation
            multi_day_result = self.daily_controller.simulate_to_end_of_regular_season()

            print()
            print(self.formatter.format_success("🏆 Regular season simulation complete!"))
            print(f"📅 Simulation Period: {multi_day_result.start_date} to {multi_day_result.end_date}")
            print(f"📊 Days Simulated: {multi_day_result.days_simulated}")
            print(f"🏈 Total Games: {multi_day_result.total_games}")
            print(f"✅ Successful Games: {multi_day_result.total_successful}")

            if multi_day_result.total_failed > 0:
                print(f"❌ Failed Games: {multi_day_result.total_failed}")

            if multi_day_result.errors:
                print(f"⚠️ Errors: {len(multi_day_result.errors)}")

            # Show final week reached
            final_status = self.controller.get_season_status()
            final_week = final_status.get('current_week', 0)
            weeks_simulated = final_week - start_week
            print(f"📈 Weeks Completed: {weeks_simulated} (from Week {start_week} to Week {final_week})")

            print()

            # Check if playoffs are now available
            if final_status.get('regular_season_complete', False):
                print(self.formatter.format_success("🎉 Regular season complete! Playoffs are now available."))
                if final_status.get('playoffs_initialized', False):
                    print(self.formatter.format_info("📋 Playoff bracket has been generated."))
                    print("You can now view standings and simulate playoff games!")
                else:
                    print(self.formatter.format_info("⏳ Playoff seeding will be calculated tomorrow."))
            else:
                print(self.formatter.format_warning("⚠️ Regular season may not be fully complete yet."))

            # Store summary for display
            self.last_day_results = {
                'date': f"{multi_day_result.start_date} to {multi_day_result.end_date}",
                'events_executed': multi_day_result.total_games,
                'successful_events': multi_day_result.total_successful,
                'failed_events': multi_day_result.total_failed,
                'errors': multi_day_result.errors
            }

            print()
            input("Press Enter to continue...")

        except Exception as e:
            print()
            print(self.formatter.format_error(f"Bulk simulation failed: {str(e)}"))
            print("You may need to simulate manually or try again.")
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

    def _select_user_team(self) -> Optional[int]:
        """
        Interactive team selection UI.

        Returns:
            Selected team ID (1-32) if successful, None if cancelled
        """
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("🏈 TEAM SELECTION"))
        print()
        print("Choose your team to manage in this dynasty:")
        print()

        # Display teams by divisions
        divisions = [
            ("AFC EAST", TeamIDs.get_division_teams("AFC_EAST")),
            ("AFC NORTH", TeamIDs.get_division_teams("AFC_NORTH")),
            ("AFC SOUTH", TeamIDs.get_division_teams("AFC_SOUTH")),
            ("AFC_WEST", TeamIDs.get_division_teams("AFC_WEST")),
            ("NFC EAST", TeamIDs.get_division_teams("NFC_EAST")),
            ("NFC NORTH", TeamIDs.get_division_teams("NFC_NORTH")),
            ("NFC SOUTH", TeamIDs.get_division_teams("NFC_SOUTH")),
            ("NFC WEST", TeamIDs.get_division_teams("NFC_WEST"))
        ]

        for division_name, team_ids in divisions:
            print(f"{division_name}:")

            # Display teams in pairs for better formatting
            for i in range(0, len(team_ids), 2):
                left_team_id = team_ids[i]
                left_team = self.team_loader.get_team_by_id(left_team_id)
                left_text = f"  {left_team_id:2d}. {left_team.full_name}"

                if i + 1 < len(team_ids):
                    right_team_id = team_ids[i + 1]
                    right_team = self.team_loader.get_team_by_id(right_team_id)
                    right_text = f"{right_team_id:2d}. {right_team.full_name}"
                    print(f"{left_text:<35} {right_text}")
                else:
                    print(left_text)
            print()

        # Get team selection
        while True:
            try:
                print("Enter team number (1-32) or 'q' to cancel: ", end="")
                choice = input().strip().lower()

                if choice == 'q':
                    return None

                team_id = int(choice)
                if 1 <= team_id <= 32:
                    # Get team and confirm
                    selected_team = self.team_loader.get_team_by_id(team_id)
                    if selected_team:
                        print()
                        print(f"Selected: {selected_team.full_name} ({selected_team.conference} {selected_team.division})")
                        print("Confirm selection? (Y/n): ", end="")
                        confirm = input().strip().lower()

                        if confirm in ['', 'y', 'yes']:
                            print()
                            print(self.formatter.format_success(f"Team selected: {selected_team.full_name}"))
                            return team_id
                        else:
                            print()
                            print("Selection cancelled. Choose again:")
                            continue
                    else:
                        print(self.formatter.format_error(f"Team {team_id} not found"))
                        continue
                else:
                    print(self.formatter.format_error("Please enter a number between 1 and 32"))
                    continue

            except ValueError:
                print(self.formatter.format_error("Please enter a valid number"))
                continue
            except KeyboardInterrupt:
                print("\nSelection cancelled.")
                return None

    def _update_dynasty_team(self, team_id: int) -> bool:
        """
        Update dynasty record with selected team.

        Args:
            team_id: Selected team ID

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Get dynasty ID from controller
            dynasty_id = self.controller.dynasty_id
            if not dynasty_id:
                print(self.formatter.format_error("No dynasty ID available for team update"))
                return False

            # Update database
            db_connection = self.controller.season_controller.season_initializer.db_connection
            success = db_connection.update_dynasty_team(dynasty_id, team_id)

            if success:
                team = self.team_loader.get_team_by_id(team_id)
                print(self.formatter.format_success(f"Dynasty updated with team: {team.full_name}"))
                return True
            else:
                print(self.formatter.format_error("Failed to update dynasty team"))
                return False

        except Exception as e:
            print(self.formatter.format_error(f"Error updating dynasty team: {e}"))
            return False

    def _initialize_user_team_manager(self, team_id: int) -> None:
        """
        Initialize UserTeamManager with selected team.

        Args:
            team_id: Selected team ID
        """
        try:
            self.user_team_manager = UserTeamManager()
            self.user_team_manager.set_user_team(team_id)

            team_name = self.user_team_manager.get_user_team_name()
            print(self.formatter.format_info(f"User team manager initialized: {team_name}"))

        except Exception as e:
            print(self.formatter.format_error(f"Error initializing user team manager: {e}"))

    def _display_playoff_status(self, status: Dict[str, Any]) -> None:
        """
        Display playoff tournament status.

        Args:
            status: Season status dictionary
        """
        print()
        print("🏆 PLAYOFF STATUS:")

        if status.get('regular_season_complete', False):
            print("  ✅ Regular season complete")
        else:
            print("  ⏳ Regular season in progress")

        if status.get('playoffs_initialized', False):
            print("  ✅ Playoffs initialized")

            # Get tournament status if available
            if hasattr(self.controller, 'playoff_tournament_manager') and self.controller.playoff_tournament_manager:
                try:
                    tournament_status = self.controller.playoff_tournament_manager.get_tournament_status()
                    print(f"  📊 Current State: {tournament_status.get('current_state', 'Unknown')}")

                    if tournament_status.get('current_round'):
                        print(f"  🏈 Current Round: {tournament_status['current_round']}")

                    if tournament_status.get('games_completed', 0) > 0:
                        games_completed = tournament_status['games_completed']
                        games_remaining = tournament_status['games_remaining']
                        print(f"  📈 Progress: {games_completed} games complete, {games_remaining} remaining")

                    # Show champions if available
                    if tournament_status.get('afc_champion'):
                        print(f"  🏆 AFC Champion: Team {tournament_status['afc_champion']}")
                    if tournament_status.get('nfc_champion'):
                        print(f"  🏆 NFC Champion: Team {tournament_status['nfc_champion']}")
                    if tournament_status.get('super_bowl_winner'):
                        print(f"  🏆 Super Bowl Champion: Team {tournament_status['super_bowl_winner']}")

                except Exception as e:
                    print(f"  ⚠️ Error retrieving tournament status: {e}")
        else:
            print("  ⏳ Playoffs not yet initialized")

        print()

    def _simulate_playoff_games(self) -> None:
        """Simulate playoff games (daily mode)."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SIMULATING PLAYOFF GAMES"))
        print()

        try:
            print(self.formatter.format_info("Simulating next playoff games..."))

            # Use the existing daily simulation to advance through playoff games
            self._simulate_next_day()

            print()
            print(self.formatter.format_success("Playoff day simulated!"))

            time.sleep(0.5)

        except Exception as e:
            print()
            print(self.formatter.format_error(f"Playoff simulation failed: {str(e)}"))
            input("Press Enter to continue...")

    def _simulate_playoff_round(self) -> None:
        """Simulate a complete playoff round (weekly mode)."""
        print(self.formatter.clear_screen())
        print(self.formatter.format_header("SIMULATING PLAYOFF ROUND"))
        print()

        try:
            print(self.formatter.format_info("Simulating next playoff round..."))

            # For weekly mode, simulate multiple days to complete a round
            # This would need integration with tournament manager to know round boundaries
            print(self.formatter.format_warning("Playoff round simulation not yet fully implemented"))
            print("For now, please switch to daily mode for playoff simulation.")

            input("Press Enter to continue...")

        except Exception as e:
            print()
            print(self.formatter.format_error(f"Playoff round simulation failed: {str(e)}"))
            input("Press Enter to continue...")