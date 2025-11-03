"""
Transaction Debug Script

Standalone debug tool for comprehensive transaction system visibility.
Shows complete probability calculations, proposal generation details, and
filter pass/fail status for all 32 teams.

Usage:
    PYTHONPATH=src python demo/transaction_debug/transaction_debug.py
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from demo.transaction_debug.debug_report_formatter import DebugReportFormatter
from transactions.transaction_ai_manager import TransactionAIManager
from team_management.gm_archetype import GMArchetype
from team_management.gm_archetype_factory import GMArchetypeFactory
from transactions.trade_proposal_generator import TeamContext
from database.dynasty_state_api import DynastyStateAPI
from database.api import DatabaseAPI


class TransactionDebugger:
    """Interactive transaction debug session."""

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize debug session.

        Args:
            database_path: Path to database (default: standard location)
        """
        self.database_path = database_path
        self.dynasty_id = "transaction_debug"
        self.season_year = 2024
        self.current_week = 3  # Week 3 (trades allowed)
        self.current_date = "2024-09-22"  # September 22, 2024 (Sunday of Week 3)

        # Initialize components
        self.dynasty_api = DynastyStateAPI(database_path)
        self.database_api = DatabaseAPI(database_path)
        self.gm_factory = GMArchetypeFactory()  # Uses default config path

        # Initialize TransactionAIManager with DEBUG MODE ENABLED
        self.transaction_ai = TransactionAIManager(
            database_path=database_path,
            dynasty_id=self.dynasty_id,
            debug_mode=True  # ✅ DEBUG MODE ENABLED
        )

        # Initialize formatter
        self.formatter = DebugReportFormatter(use_colors=True)

        # Collected debug data across days
        self.all_debug_data = []

        print(f"\n{'='*80}")
        print(f"{'TRANSACTION DEBUG SESSION INITIALIZED'.center(80)}")
        print(f"{'='*80}")
        print(f"Database: {database_path}")
        print(f"Dynasty: {self.dynasty_id}")
        print(f"Season: {self.season_year}")
        print(f"Current Date: {self.current_date} (Week {self.current_week})")
        print(f"Debug Mode: ENABLED ✓")
        print(f"{'='*80}\n")

    def run_interactive_menu(self):
        """Run interactive debug menu."""
        while True:
            print(f"\n{'='*80}")
            print("TRANSACTION DEBUG MENU")
            print(f"{'='*80}")
            print("Current Date:", self.current_date, f"(Week {self.current_week})")
            print("")
            print("1. Simulate 1 day with full transaction trace")
            print("2. Simulate 7 days (1 week) with daily reports")
            print("3. Simulate custom number of days")
            print("4. Show multi-day summary")
            print("5. Exit")
            print(f"{'='*80}")

            choice = input("\nEnter choice (1-5): ").strip()

            if choice == "1":
                self.simulate_single_day()
            elif choice == "2":
                self.simulate_multiple_days(7)
            elif choice == "3":
                try:
                    num_days = int(input("Enter number of days to simulate: ").strip())
                    if num_days > 0:
                        self.simulate_multiple_days(num_days)
                    else:
                        print("❌ Please enter a positive number")
                except ValueError:
                    print("❌ Invalid input")
            elif choice == "4":
                self.show_multi_day_summary()
            elif choice == "5":
                print("\n👋 Exiting debug session...")
                break
            else:
                print("❌ Invalid choice. Please enter 1-5.")

    def simulate_single_day(self):
        """Simulate a single day with full transaction trace."""
        print(f"\n{'='*80}")
        print(f"SIMULATING SINGLE DAY: {self.current_date} (Week {self.current_week})")
        print(f"{'='*80}\n")

        # Collect debug data for all 32 teams
        day_debug_data = {
            'date': self.current_date,
            'phase': 'REGULAR_SEASON',
            'week': self.current_week,
            'teams_evaluated': []
        }

        for team_id in range(1, 33):
            try:
                # Get team record (mock for now - replace with actual standings)
                team_record = self._get_team_record(team_id)

                # Assess team situation to get GM archetype
                gm = self._get_gm_archetype(team_id)
                team_context = self._get_team_context(team_id, team_record)

                # Evaluate transactions for this team (debug_mode already enabled)
                proposals, debug_info = self.transaction_ai.evaluate_daily_transactions(
                    team_id=team_id,
                    current_date=self.current_date,
                    season_phase="regular_season",
                    team_record=team_record,
                    current_week=self.current_week
                )

                # Add team name
                team_name = self._get_team_name(team_id)
                debug_info['team_name'] = team_name

                # Store debug info
                day_debug_data['teams_evaluated'].append(debug_info)

            except Exception as e:
                print(f"⚠️  Error evaluating Team {team_id}: {e}")
                continue

        # Store this day's data
        self.all_debug_data.append(day_debug_data)

        # Format and display report
        report = self.formatter.format_daily_report(day_debug_data)
        print(report)

        # Advance to next day
        self._advance_day()

    def simulate_multiple_days(self, num_days: int):
        """
        Simulate multiple days with daily reports.

        Args:
            num_days: Number of days to simulate
        """
        print(f"\n{'='*80}")
        print(f"SIMULATING {num_days} DAYS")
        print(f"Starting: {self.current_date} (Week {self.current_week})")
        print(f"{'='*80}\n")

        for day_num in range(num_days):
            print(f"\n{'─'*80}")
            print(f"DAY {day_num + 1}/{num_days}")
            print(f"{'─'*80}")

            self.simulate_single_day()

            # Pause between days (optional)
            if day_num < num_days - 1:
                input("\nPress Enter to continue to next day...")

        print(f"\n{'='*80}")
        print(f"{num_days} DAYS SIMULATION COMPLETE")
        print(f"{'='*80}")

    def show_multi_day_summary(self):
        """Show summary across all simulated days."""
        if len(self.all_debug_data) == 0:
            print("\n⚠️  No data available. Simulate some days first!")
            return

        print(f"\n{'='*80}")
        print("MULTI-DAY SUMMARY")
        print(f"{'='*80}\n")

        summary = self.formatter.format_multi_day_summary(self.all_debug_data)
        print(summary)

    def _advance_day(self):
        """Advance to next day."""
        # Parse current date
        date_obj = datetime.strptime(self.current_date, '%Y-%m-%d')

        # Add 1 day
        next_date = date_obj + timedelta(days=1)
        self.current_date = next_date.strftime('%Y-%m-%d')

        # Update week (simplified - assume each week starts Monday)
        # Week 1 starts Sept 5 (Thursday), so Week 3 starts Sept 19
        # This is a simplified calculation
        days_since_sept_5 = (next_date - datetime(2024, 9, 5)).days
        self.current_week = min((days_since_sept_5 // 7) + 1, 18)

    def _get_team_record(self, team_id: int) -> Dict[str, int]:
        """
        Get team record.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with wins, losses, ties
        """
        # Try to get from database
        try:
            standings = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year,
                season_type="regular_season"
            )

            # Find this team in standings
            for division_name, teams in standings.get('divisions', {}).items():
                for team_data in teams:
                    if team_data['team_id'] == team_id:
                        standing = team_data['standing']
                        return {
                            'wins': standing.wins,
                            'losses': standing.losses,
                            'ties': standing.ties
                        }
        except Exception:
            pass

        # Fallback: generate mock record
        import random
        wins = random.randint(0, 2)
        losses = 2 - wins
        return {'wins': wins, 'losses': losses, 'ties': 0}

    def _get_gm_archetype(self, team_id: int) -> GMArchetype:
        """Get GM archetype for team."""
        return self.gm_factory.get_gm_for_team(team_id)

    def _get_team_context(self, team_id: int, team_record: Dict[str, int]) -> TeamContext:
        """Create team context."""
        return TeamContext(
            team_id=team_id,
            wins=team_record['wins'],
            losses=team_record['losses'],
            ties=team_record.get('ties', 0),
            cap_space=50000000,  # Mock cap space
            season="regular"
        )

    def _get_team_name(self, team_id: int) -> str:
        """Get team name from team ID."""
        team_names = {
            1: "Bills", 2: "Dolphins", 3: "Patriots", 4: "Jets",
            5: "Ravens", 6: "Bengals", 7: "Browns", 8: "Steelers",
            9: "Texans", 10: "Colts", 11: "Jaguars", 12: "Titans",
            13: "Broncos", 14: "Chiefs", 15: "Raiders", 16: "Chargers",
            17: "Cowboys", 18: "Giants", 19: "Eagles", 20: "Commanders",
            21: "Bears", 22: "Lions", 23: "Packers", 24: "Vikings",
            25: "Falcons", 26: "Panthers", 27: "Saints", 28: "Buccaneers",
            29: "Cardinals", 30: "Rams", 31: "49ers", 32: "Seahawks"
        }
        return team_names.get(team_id, f"Team {team_id}")


def main():
    """Main entry point."""
    from datetime import timedelta  # Import here for _advance_day

    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + "TRANSACTION DEBUG SYSTEM".center(78) + "║")
    print("║" + "Complete visibility into AI transaction decision-making".center(78) + "║")
    print("╚" + "═"*78 + "╝")
    print("")

    # Initialize debugger
    debugger = TransactionDebugger()

    # Run interactive menu
    debugger.run_interactive_menu()

    print("\n✅ Debug session complete.\n")


if __name__ == "__main__":
    main()
