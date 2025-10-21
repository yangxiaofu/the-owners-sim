"""
NFL Offseason Simulation Demo

Interactive terminal demo for testing the OffseasonController.

This demo allows you to:
- Navigate through NFL offseason phases (franchise tags → free agency → draft → roster cuts)
- Apply franchise/transition tags to players
- Browse and sign free agents
- Make draft selections
- Manage roster cuts
- Advance the calendar day-by-day or jump to deadlines

Usage:
    python demo/offseason_demo/offseason_demo.py

    OR

    PYTHONPATH=src python demo/offseason_demo/offseason_demo.py
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Add src directory to path if not already there
# This allows the demo to be run from anywhere
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from offseason.offseason_controller import OffseasonController
from offseason.offseason_phases import OffseasonPhase


class OffseasonDemo:
    """Interactive terminal demo for NFL offseason simulation."""

    @staticmethod
    def format_date(date_obj, format_string='%B %d, %Y'):
        """
        Format a date object (handles custom Date objects).

        Args:
            date_obj: Date object (custom Date or datetime)
            format_string: strftime format string

        Returns:
            Formatted date string
        """
        # Convert custom Date object to python date
        if hasattr(date_obj, 'to_python_date'):
            py_date = date_obj.to_python_date()
        else:
            py_date = date_obj

        # Format the date
        if hasattr(py_date, 'strftime'):
            return py_date.strftime(format_string)
        else:
            # Fallback
            return f"{py_date.month}/{py_date.day}/{py_date.year}"

    def __init__(self):
        """Initialize the demo."""
        # Demo configuration
        self.database_path = "data/database/nfl_simulation.db"
        self.dynasty_id = "offseason_demo"
        self.season_year = 2024
        self.user_team_id = 9  # New England Patriots (for demo)

        # Initialize controller
        print("=" * 80)
        print("NFL OFFSEASON SIMULATION DEMO".center(80))
        print("=" * 80)
        print()
        print("Initializing offseason controller...")
        print(f"  Dynasty: {self.dynasty_id}")
        print(f"  Season: {self.season_year}")
        print(f"  User Team: Team {self.user_team_id}")
        print()

        # Start after Super Bowl (February 9, 2025)
        super_bowl_date = datetime(2025, 2, 9)

        self.controller = OffseasonController(
            database_path=self.database_path,
            dynasty_id=self.dynasty_id,
            season_year=self.season_year,
            user_team_id=self.user_team_id,
            super_bowl_date=super_bowl_date,
            enable_persistence=True,
            verbose_logging=True
        )

        print("Controller initialized successfully!")
        print()

    def run(self):
        """Run the interactive demo."""
        while True:
            self.show_main_menu()
            choice = input("\nEnter choice: ").strip()

            if choice == '1':
                self.show_state_summary()
            elif choice == '2':
                self.advance_calendar_menu()
            elif choice == '3':
                self.franchise_tag_menu()
            elif choice == '4':
                self.free_agency_menu()
            elif choice == '5':
                self.draft_menu()
            elif choice == '6':
                self.roster_menu()
            elif choice == '7':
                self.show_actions_taken()
            elif choice == 'q':
                print("\nExiting offseason demo. Goodbye!")
                break
            else:
                print("\nInvalid choice. Please try again.")

            input("\nPress Enter to continue...")

    def show_main_menu(self):
        """Display the main menu."""
        print("\n" + "=" * 80)
        print("NFL OFFSEASON DEMO - MAIN MENU".center(80))
        print("=" * 80)

        # Show current state
        state = self.controller.get_state_summary()
        current_date = state['current_date']
        current_phase = state['current_phase']

        print(f"\nCurrent Date: {self.format_date(current_date, '%B %d, %Y (%A)')}")
        print(f"Current Phase: {current_phase.replace('_', ' ').title()}")
        print(f"Actions Taken: {state['actions_taken']}")

        # Show next deadline
        deadlines = state['upcoming_deadlines']
        if deadlines:
            next_deadline = deadlines[0]
            print(f"\nNext Deadline: {next_deadline['description']}")
            print(f"  Date: {self.format_date(next_deadline['date'], '%B %d, %Y')}")
            print(f"  Days Away: {next_deadline['days_remaining']}")

        print("\n" + "-" * 80)
        print("1. View State Summary")
        print("2. Advance Calendar")
        print("3. Franchise Tag Operations")
        print("4. Free Agency Operations")
        print("5. Draft Operations")
        print("6. Roster Management")
        print("7. View Actions Taken")
        print("Q. Quit")
        print("-" * 80)

    def show_state_summary(self):
        """Display comprehensive state summary."""
        print("\n" + "=" * 80)
        print("OFFSEASON STATE SUMMARY".center(80))
        print("=" * 80)

        state = self.controller.get_state_summary()

        print(f"\nDynasty ID: {state['dynasty_id']}")
        print(f"Season Year: {state['season_year']}")
        print(f"Current Date: {self.format_date(state['current_date'], '%B %d, %Y (%A)')}")
        print(f"Current Phase: {state['current_phase'].replace('_', ' ').title()}")
        print(f"Offseason Complete: {state['offseason_complete']}")
        print(f"Actions Taken: {state['actions_taken']}")

        print("\n" + "-" * 80)
        print("UPCOMING DEADLINES:")
        print("-" * 80)

        for i, deadline in enumerate(state['upcoming_deadlines'], 1):
            print(f"\n{i}. {deadline['description']}")
            print(f"   Date: {self.format_date(deadline['date'], '%B %d, %Y')}")
            print(f"   Days Away: {deadline['days_remaining']}")
            print(f"   Action: {deadline['action']}")

    def advance_calendar_menu(self):
        """Calendar advancement submenu."""
        print("\n" + "=" * 80)
        print("CALENDAR ADVANCEMENT".center(80))
        print("=" * 80)
        print("\n1. Advance 1 Day")
        print("2. Advance 1 Week")
        print("3. Advance to Next Deadline")
        print("4. Advance to Specific Deadline")
        print("5. Jump to Training Camp")
        print("B. Back to Main Menu")

        choice = input("\nEnter choice: ").strip()

        if choice == '1':
            print("\nAdvancing 1 day...")
            result = self.controller.advance_day()
            self.show_advancement_result(result)

        elif choice == '2':
            print("\nAdvancing 1 week (7 days)...")
            for _ in range(7):
                result = self.controller.advance_day()
            self.show_advancement_result(result)

        elif choice == '3':
            deadlines = self.controller.get_upcoming_deadlines(1)
            if deadlines:
                deadline = deadlines[0]
                print(f"\nAdvancing to {deadline['description']}...")
                result = self.controller.advance_to_deadline(deadline['type'])
                print(f"\nAdvanced {result['days_advanced']} days")
                print(f"Current Phase: {result['current_phase']}")

        elif choice == '4':
            self.show_deadline_selection()

        elif choice == '5':
            confirm = input("\nJump to training camp? This will skip the entire offseason (y/n): ")
            if confirm.lower() == 'y':
                result = self.controller.advance_to_training_camp()
                print(f"\nJumped to training camp!")
                print(f"Advanced {result['days_advanced']} days")

    def show_deadline_selection(self):
        """Show deadline selection menu."""
        deadlines = self.controller.get_upcoming_deadlines(10)

        print("\n" + "-" * 80)
        print("SELECT DEADLINE TO ADVANCE TO:")
        print("-" * 80)

        for i, deadline in enumerate(deadlines, 1):
            print(f"{i}. {deadline['description']} ({self.format_date(deadline['date'], '%B %d')})")

        choice = input("\nEnter deadline number: ").strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(deadlines):
                deadline = deadlines[idx]
                result = self.controller.advance_to_deadline(deadline['type'])
                print(f"\nAdvanced {result['days_advanced']} days to {deadline['description']}")
            else:
                print("\nInvalid deadline number.")
        except ValueError:
            print("\nInvalid input.")

    def show_advancement_result(self, result):
        """Display advancement result."""
        print(f"\nNew Date: {self.format_date(result['new_date'], '%B %d, %Y (%A)')}")

        if result['phase_changed']:
            print(f"Phase Changed: {result['new_phase'].replace('_', ' ').title()}")

        if result['deadlines_passed']:
            print(f"Deadlines Passed: {', '.join(result['deadlines_passed'])}")

        if result['events_triggered']:
            print(f"Events Triggered: {len(result['events_triggered'])}")

    def franchise_tag_menu(self):
        """Franchise tag operations submenu."""
        print("\n" + "=" * 80)
        print("FRANCHISE TAG OPERATIONS".center(80))
        print("=" * 80)
        print("\n1. View Tag Candidates")
        print("2. Apply Franchise Tag (Non-Exclusive)")
        print("3. Apply Franchise Tag (Exclusive)")
        print("4. Apply Transition Tag")
        print("5. Check Team Tag Status")
        print("B. Back to Main Menu")

        choice = input("\nEnter choice: ").strip()

        if choice == '1':
            self.show_tag_candidates()
        elif choice == '2':
            self.apply_franchise_tag_demo("NON_EXCLUSIVE")
        elif choice == '3':
            self.apply_franchise_tag_demo("EXCLUSIVE")
        elif choice == '4':
            self.apply_transition_tag_demo()
        elif choice == '5':
            self.show_team_tag_status()

    def show_tag_candidates(self):
        """Show franchise tag candidates."""
        print("\n" + "-" * 80)
        print("FRANCHISE TAG CANDIDATES")
        print("-" * 80)

        candidates = self.controller.get_franchise_tag_candidates(self.user_team_id)

        if not candidates:
            print("\nNo franchise tag candidates found.")
            print("(This is a demo - player data not yet integrated)")
        else:
            for i, player in enumerate(candidates, 1):
                print(f"\n{i}. {player['name']} ({player['position']})")
                print(f"   Franchise Tag Salary: ${player['franchise_tag_salary']:,}")
                print(f"   Transition Tag Salary: ${player['transition_tag_salary']:,}")

    def apply_franchise_tag_demo(self, tag_type: str):
        """Apply franchise tag demo."""
        print(f"\n{tag_type} FRANCHISE TAG DEMO")
        print("-" * 80)
        print("\nThis is a demo. Enter a test player_id and team_id.")

        try:
            player_id = int(input("Player ID: ").strip())
            team_id = int(input("Team ID (1-32): ").strip())

            result = self.controller.apply_franchise_tag(
                player_id=player_id,
                team_id=team_id,
                tag_type=tag_type
            )

            print(f"\n✓ {tag_type} Franchise Tag Applied!")
            print(f"  Tag Salary: ${result['tag_salary']:,}")
            print(f"  Consecutive Tag #: {result['consecutive_tag_number']}")
            print(f"  Cap Space Remaining: ${result['cap_space_remaining']:,}")

        except ValueError as e:
            print(f"\n✗ Error: {e}")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")

    def apply_transition_tag_demo(self):
        """Apply transition tag demo."""
        print("\nTRANSITION TAG DEMO")
        print("-" * 80)
        print("\nThis is a demo. Enter a test player_id and team_id.")

        try:
            player_id = int(input("Player ID: ").strip())
            team_id = int(input("Team ID (1-32): ").strip())

            result = self.controller.apply_transition_tag(
                player_id=player_id,
                team_id=team_id
            )

            print(f"\n✓ Transition Tag Applied!")
            print(f"  Tag Salary: ${result['tag_salary']:,}")

        except ValueError as e:
            print(f"\n✗ Error: {e}")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")

    def show_team_tag_status(self):
        """Show team tag status."""
        team_id = int(input("\nTeam ID (1-32): ").strip())

        status = self.controller.get_team_tag_status(team_id)

        print("\n" + "-" * 80)
        print(f"TEAM {team_id} TAG STATUS")
        print("-" * 80)
        print(f"Franchise Tags Used: {status['franchise']}")
        print(f"Transition Tags Used: {status['transition']}")
        print(f"Total Tags Used: {status['total']}")
        print(f"Can Apply Tag: {'Yes' if status['can_apply_tag'] else 'No'}")

    def free_agency_menu(self):
        """Free agency operations submenu."""
        print("\n" + "=" * 80)
        print("FREE AGENCY OPERATIONS".center(80))
        print("=" * 80)
        print("\n1. Browse Free Agent Pool")
        print("2. Sign Free Agent")
        print("3. Apply RFA Tender")
        print("4. Simulate AI Free Agency (30 days)")
        print("B. Back to Main Menu")

        choice = input("\nEnter choice: ").strip()

        if choice == '1':
            self.browse_free_agents()
        elif choice == '2':
            self.sign_free_agent_demo()
        elif choice == '3':
            self.apply_rfa_tender_demo()
        elif choice == '4':
            self.simulate_ai_fa()

    def browse_free_agents(self):
        """Browse free agent pool."""
        print("\n" + "-" * 80)
        print("FREE AGENT POOL")
        print("-" * 80)

        free_agents = self.controller.get_free_agent_pool(limit=20)

        if not free_agents:
            print("\nNo free agents found.")
            print("(This is a demo - free agent pool not yet populated)")
        else:
            for i, player in enumerate(free_agents, 1):
                print(f"\n{i}. {player['name']} ({player['position']})")
                print(f"   Type: {player['fa_type']}")
                print(f"   Market Value: {player['market_value']}")

    def sign_free_agent_demo(self):
        """Sign free agent demo."""
        print("\nFREE AGENT SIGNING DEMO")
        print("-" * 80)
        print("\nThis is a demo. Enter test contract terms.")

        try:
            player_id = int(input("Player ID: ").strip())
            team_id = int(input("Team ID (1-32): ").strip())
            years = int(input("Contract Years (1-7): ").strip())
            annual_salary = int(input("Annual Salary ($): ").strip())
            signing_bonus = int(input("Signing Bonus ($, optional): ").strip() or "0")
            guarantees = int(input("Guarantees ($, optional): ").strip() or "0")

            result = self.controller.sign_free_agent(
                player_id=player_id,
                team_id=team_id,
                years=years,
                annual_salary=annual_salary,
                signing_bonus=signing_bonus,
                guarantees=guarantees
            )

            print(f"\n✓ Free Agent Signed!")
            print(f"  Contract: {result['contract_details']['years']} years, "
                  f"${result['contract_details']['aav']:,}/year")
            print(f"  Total Value: ${result['contract_details']['total_value']:,}")
            print(f"  Year 1 Cap Hit: ${result['cap_hit_year1']:,}")
            print(f"  Cap Space Remaining: ${result['cap_space_remaining']:,}")

        except ValueError as e:
            print(f"\n✗ Error: {e}")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")

    def apply_rfa_tender_demo(self):
        """Apply RFA tender demo."""
        print("\nRFA TENDER DEMO")
        print("-" * 80)
        print("\nTender Levels:")
        print("  1. FIRST_ROUND (1st round compensation)")
        print("  2. SECOND_ROUND (2nd round compensation)")
        print("  3. ORIGINAL_ROUND (original draft round compensation)")
        print("  4. RIGHT_OF_FIRST_REFUSAL (no compensation)")

        try:
            player_id = int(input("\nPlayer ID: ").strip())
            team_id = int(input("Team ID (1-32): ").strip())
            tender_choice = input("Tender Level (1-4): ").strip()

            tender_map = {
                '1': 'FIRST_ROUND',
                '2': 'SECOND_ROUND',
                '3': 'ORIGINAL_ROUND',
                '4': 'RIGHT_OF_FIRST_REFUSAL'
            }

            tender_level = tender_map.get(tender_choice)
            if not tender_level:
                print("\nInvalid tender level.")
                return

            result = self.controller.apply_rfa_tender(
                player_id=player_id,
                team_id=team_id,
                tender_level=tender_level
            )

            print(f"\n✓ RFA Tender Applied!")
            print(f"  Tender Level: {result['tender_level']}")
            print(f"  Tender Salary: ${result['tender_salary']:,}")
            print(f"  Compensation: {result['compensation']}")

        except ValueError as e:
            print(f"\n✗ Error: {e}")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")

    def simulate_ai_fa(self):
        """Simulate AI free agency."""
        print("\nSIMULATING AI FREE AGENCY (30 DAYS)...")
        print("-" * 80)

        signings = self.controller.simulate_ai_free_agency(
            user_team_id=self.user_team_id,
            days_to_simulate=30
        )

        print(f"\nAI teams made {len(signings)} free agent signings")

    def draft_menu(self):
        """Draft operations submenu."""
        print("\n" + "=" * 80)
        print("DRAFT OPERATIONS".center(80))
        print("=" * 80)
        print("\n1. View Draft Board")
        print("2. Make Draft Selection")
        print("3. Simulate Draft Round")
        print("4. Simulate Entire Draft")
        print("5. View Team Draft Picks")
        print("B. Back to Main Menu")

        choice = input("\nEnter choice: ").strip()

        if choice == '1':
            self.view_draft_board()
        elif choice == '2':
            self.make_draft_pick_demo()
        elif choice == '3':
            self.simulate_draft_round_demo()
        elif choice == '4':
            self.simulate_entire_draft_demo()
        elif choice == '5':
            self.view_team_draft_picks()

    def view_draft_board(self):
        """View team's draft board."""
        print("\n" + "-" * 80)
        print(f"DRAFT BOARD - TEAM {self.user_team_id}")
        print("-" * 80)

        board = self.controller.get_draft_board(self.user_team_id, limit=20)

        if not board:
            print("\nDraft board empty.")
            print("(This is a demo - draft class not yet generated)")

    def make_draft_pick_demo(self):
        """Make draft selection demo."""
        print("\nDRAFT SELECTION DEMO")
        print("-" * 80)

        try:
            round_num = int(input("Round (1-7): ").strip())
            pick_num = int(input("Pick Number: ").strip())
            player_id = input("Player ID: ").strip()
            team_id = int(input("Team ID (1-32): ").strip())

            result = self.controller.make_draft_selection(
                round_num=round_num,
                pick_num=pick_num,
                player_id=player_id,
                team_id=team_id
            )

            print(f"\n✓ Draft Pick Made!")
            print(f"  Round {result['round']}, Pick {result['pick']}")
            print(f"  Overall Pick: #{result['overall_pick']}")

        except ValueError as e:
            print(f"\n✗ Error: {e}")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")

    def simulate_draft_round_demo(self):
        """Simulate single draft round."""
        round_num = int(input("\nRound to simulate (1-7): ").strip())

        picks = self.controller.simulate_draft_round(
            round_num=round_num,
            user_team_id=self.user_team_id
        )

        print(f"\nRound {round_num} simulated: {len(picks)} picks made")

    def simulate_entire_draft_demo(self):
        """Simulate entire draft."""
        confirm = input("\nSimulate entire draft (7 rounds)? (y/n): ")
        if confirm.lower() == 'y':
            result = self.controller.simulate_entire_draft(
                user_team_id=self.user_team_id
            )

            print(f"\n✓ Draft Complete!")
            print(f"  Total Picks: {result['total_picks']}")
            print(f"  Your Team's Picks: {len(result['user_team_picks'])}")

    def view_team_draft_picks(self):
        """View team's draft picks."""
        team_id = int(input("\nTeam ID (1-32): ").strip())

        picks = self.controller.get_team_draft_picks(team_id)

        print(f"\nTeam {team_id} has {len(picks)} draft picks")

    def roster_menu(self):
        """Roster management submenu."""
        print("\n" + "=" * 80)
        print("ROSTER MANAGEMENT".center(80))
        print("=" * 80)
        print("\n1. View Team Roster")
        print("2. Cut Player")
        print("3. Finalize 53-Man Roster")
        print("B. Back to Main Menu")

        choice = input("\nEnter choice: ").strip()

        if choice == '1':
            self.view_roster()
        elif choice == '2':
            self.cut_player_demo()
        elif choice == '3':
            self.finalize_roster_demo()

    def view_roster(self):
        """View team roster."""
        team_id = int(input("\nTeam ID (1-32): ").strip())
        include_ps = input("Include practice squad? (y/n): ").lower() == 'y'

        roster = self.controller.get_roster(team_id, include_practice_squad=include_ps)

        print(f"\n" + "-" * 80)
        print(f"TEAM {team_id} ROSTER")
        print("-" * 80)
        print(f"\nRoster Size: {len(roster)}")

    def cut_player_demo(self):
        """Cut player demo."""
        print("\nCUT PLAYER DEMO")
        print("-" * 80)

        try:
            player_id = int(input("Player ID: ").strip())
            team_id = int(input("Team ID (1-32): ").strip())
            june_1 = input("June 1 designation? (y/n): ").lower() == 'y'

            result = self.controller.cut_player(
                team_id=team_id,
                player_id=player_id,
                june_1_designation=june_1
            )

            print(f"\n✓ Player Cut!")
            print(f"  Dead Money: ${result['dead_money']:,}")
            print(f"  Cap Savings: ${result['cap_savings']:,}")
            print(f"  Cap Space Remaining: ${result['cap_space_remaining']:,}")

        except Exception as e:
            print(f"\n✗ Error: {e}")

    def finalize_roster_demo(self):
        """Finalize 53-man roster."""
        team_id = int(input("\nTeam ID (1-32): ").strip())

        result = self.controller.finalize_53_man_roster(team_id)

        if result.get('finalized'):
            print(f"\n✓ Roster Finalized!")
            print(f"  Roster Size: {result['roster_size']}")
        else:
            print(f"\n✗ Roster Not Valid")
            print(f"  Violations: {result.get('violations')}")

    def show_actions_taken(self):
        """Show all actions taken this offseason."""
        print("\n" + "=" * 80)
        print("ACTIONS TAKEN THIS OFFSEASON".center(80))
        print("=" * 80)

        actions = self.controller.actions_taken

        if not actions:
            print("\nNo actions taken yet.")
        else:
            for i, action in enumerate(actions, 1):
                print(f"\n{i}. {action['type']}")
                print(f"   Date: {self.format_date(action['date'], '%B %d, %Y')}")
                for key, value in action.items():
                    if key not in ['type', 'date']:
                        print(f"   {key}: {value}")


def main():
    """Main entry point."""
    try:
        demo = OffseasonDemo()
        demo.run()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
