"""
NFL Salary Cap Calculator Demo

Interactive terminal demonstration of the CapCalculator system showcasing:
- League-wide cap summaries
- Team-specific cap analysis
- Top contract displays
- Dead money calculations
- Contract restructuring
- Cap compliance validation
- Database statistics

This demo provides a comprehensive view of salary cap management capabilities
using the CapCalculator, CapDatabaseAPI, and display formatting utilities.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from salary_cap.cap_calculator import CapCalculator
from salary_cap.cap_database_api import CapDatabaseAPI
from salary_cap.cap_utils import format_currency, format_cap_summary
from constants.team_ids import TeamIDs


class CapDisplayFormatter:
    """
    Terminal display formatter for salary cap data.

    Provides formatted tables, summaries, and reports with box-drawing
    characters and color coding for better readability.
    """

    # Box-drawing characters
    BOX_TOP_LEFT = "╔"
    BOX_TOP_RIGHT = "╗"
    BOX_BOTTOM_LEFT = "╚"
    BOX_BOTTOM_RIGHT = "╝"
    BOX_HORIZONTAL = "═"
    BOX_VERTICAL = "║"
    BOX_T_DOWN = "╦"
    BOX_T_UP = "╩"
    BOX_T_RIGHT = "╠"
    BOX_T_LEFT = "╣"
    BOX_CROSS = "╬"

    # Status symbols
    STATUS_COMPLIANT = "✓"
    STATUS_OVER_CAP = "✗"
    STATUS_WARNING = "⚠"

    @staticmethod
    def format_team_name(team_id: int) -> str:
        """
        Get formatted team name from team_id.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Team name string
        """
        teams_data_path = Path(__file__).parent.parent.parent / "src" / "data" / "teams.json"

        try:
            with open(teams_data_path, 'r') as f:
                teams_data = json.load(f)
                team_info = teams_data['teams'].get(str(team_id))
                if team_info:
                    return team_info['full_name']
        except Exception:
            pass

        return f"Team {team_id}"

    @staticmethod
    def format_header(title: str, width: int = 80) -> str:
        """
        Format header with box-drawing characters.

        Args:
            title: Header title
            width: Total width of header

        Returns:
            Formatted header string
        """
        lines = []

        # Top border
        lines.append(CapDisplayFormatter.BOX_TOP_LEFT +
                    CapDisplayFormatter.BOX_HORIZONTAL * (width - 2) +
                    CapDisplayFormatter.BOX_TOP_RIGHT)

        # Title (centered)
        padding = (width - 2 - len(title)) // 2
        lines.append(CapDisplayFormatter.BOX_VERTICAL +
                    " " * padding + title + " " * (width - 2 - padding - len(title)) +
                    CapDisplayFormatter.BOX_VERTICAL)

        # Bottom border
        lines.append(CapDisplayFormatter.BOX_BOTTOM_LEFT +
                    CapDisplayFormatter.BOX_HORIZONTAL * (width - 2) +
                    CapDisplayFormatter.BOX_BOTTOM_RIGHT)

        return "\n".join(lines)

    @staticmethod
    def format_table_row(columns: List[str], widths: List[int], separator: str = "│") -> str:
        """
        Format table row with specified column widths.

        Args:
            columns: List of column values
            widths: List of column widths
            separator: Column separator character

        Returns:
            Formatted row string
        """
        parts = []
        for col, width in zip(columns, widths):
            # Truncate if too long
            if len(col) > width:
                col = col[:width-3] + "..."
            parts.append(col.ljust(width))

        return f"{separator} " + f" {separator} ".join(parts) + f" {separator}"

    @staticmethod
    def format_separator(widths: List[int], left: str = "├", mid: str = "┼", right: str = "┤", horiz: str = "─") -> str:
        """
        Format table separator line.

        Args:
            widths: List of column widths
            left: Left edge character
            mid: Middle intersection character
            right: Right edge character
            horiz: Horizontal line character

        Returns:
            Formatted separator string
        """
        parts = [horiz * (w + 2) for w in widths]
        return left + mid.join(parts) + right


class CapDemoApp:
    """
    Interactive NFL Salary Cap Calculator Demo Application.

    Provides menu-driven interface for exploring salary cap data and calculations.
    """

    def __init__(self, database_path: str = "demo/cap_calculator_demo/cap_demo.db"):
        """
        Initialize demo application.

        Args:
            database_path: Path to SQLite database
        """
        self.calculator = CapCalculator(database_path)
        self.db_api = CapDatabaseAPI(database_path)
        self.formatter = CapDisplayFormatter()

        # Default dynasty and season
        self.dynasty_id = "demo_dynasty"
        self.current_season = 2025

        # Initialize sample data
        self._initialize_sample_data()

    def _initialize_sample_data(self) -> None:
        """
        Initialize sample salary cap data for demonstration.

        Creates base cap limits for all 32 teams with realistic 2025 salary cap.
        """
        # 2025 projected salary cap: $255M
        salary_cap_2025 = 255_000_000

        try:
            # Initialize league-wide cap for 2025 if not exists
            existing_cap = self.db_api.get_salary_cap_for_season(self.current_season)
            if not existing_cap:
                # Would need to insert into league_salary_cap_history table
                # For demo, just note this in console
                print(f"\nNote: Using salary cap of {format_currency(salary_cap_2025)} for {self.current_season}")

            # Initialize team caps for all 32 teams
            import random
            for team_id in range(1, 33):
                existing_summary = self.db_api.get_team_cap_summary(
                    team_id,
                    self.current_season,
                    self.dynasty_id
                )

                if not existing_summary:
                    # Random carryover between -$5M and +$15M
                    carryover = random.randint(-5_000_000, 15_000_000)

                    self.db_api.initialize_team_cap(
                        team_id=team_id,
                        season=self.current_season,
                        dynasty_id=self.dynasty_id,
                        salary_cap_limit=salary_cap_2025,
                        carryover_from_previous=carryover
                    )

                # Always set realistic committed amounts (70-95% of cap) for demo
                # This ensures demo shows realistic values even if database was pre-initialized
                committed_pct = random.uniform(0.70, 0.95)
                committed_amount = int(salary_cap_2025 * committed_pct)

                self.db_api.update_team_cap(
                    team_id=team_id,
                    season=self.current_season,
                    dynasty_id=self.dynasty_id,
                    active_contracts_total=committed_amount,
                    dead_money_total=random.randint(0, 15_000_000),
                    ltbe_incentives_total=random.randint(0, 3_000_000),
                    practice_squad_total=random.randint(1_000_000, 2_500_000),
                    top_51_total=committed_amount,  # In offseason, top-51 = active contracts for demo
                    is_top_51_active=True
                )

        except Exception as e:
            print(f"\nWarning: Could not initialize all sample data: {e}")

    def run(self) -> None:
        """
        Run the main demo application loop.
        """
        while True:
            self.show_menu()
            choice = input("\nChoice: ").strip()

            if choice == "0":
                print("\nExiting NFL Salary Cap Calculator Demo. Goodbye!")
                break

            try:
                if choice == "1":
                    self.show_all_teams_summary()
                elif choice == "2":
                    self.show_team_details()
                elif choice == "3":
                    self.show_top_cap_hits()
                elif choice == "4":
                    self.show_teams_by_cap_space()
                elif choice == "5":
                    self.test_player_release()
                elif choice == "6":
                    self.test_contract_restructure()
                elif choice == "7":
                    self.validate_team_compliance()
                elif choice == "8":
                    self.show_database_stats()
                else:
                    print("\n❌ Invalid choice. Please select 0-8.")

            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()

            input("\nPress Enter to continue...")

    def show_menu(self) -> None:
        """Display main menu."""
        menu = f"""
{self.formatter.format_header("NFL SALARY CAP CALCULATOR DEMO - 2025 Season", 80)}

1. Show All Teams Cap Summary
2. Show Specific Team Details
3. Show Top 10 Highest Cap Hits
4. Show Teams by Available Cap Space
5. Test Player Release (Dead Money Calculator)
6. Test Contract Restructure
7. Validate Team Cap Compliance
8. Show Database Statistics
0. Exit
"""
        print(menu)

    def show_all_teams_summary(self) -> None:
        """
        Display summary table of all 32 teams' cap situations.

        Shows cap limit, committed, available space, and compliance status.
        """
        print(f"\n{self.formatter.format_header('ALL TEAMS SALARY CAP SUMMARY', 120)}\n")

        # Table headers
        widths = [25, 18, 18, 18, 18, 12]
        headers = ["Team", "Cap Limit", "Committed", "Available", "Dead Money", "Status"]

        # Top border
        print("┌" + "─" * (sum(widths) + len(widths) * 3 - 1) + "┐")
        print(self.formatter.format_table_row(headers, widths))
        print(self.formatter.format_separator(widths, "├", "┼", "┤", "─"))

        # Get all teams
        teams_data = []
        for team_id in range(1, 33):
            try:
                cap_space = self.calculator.calculate_team_cap_space(
                    team_id,
                    self.current_season,
                    self.dynasty_id,
                    roster_mode="offseason"
                )

                summary = self.db_api.get_team_cap_summary(
                    team_id,
                    self.current_season,
                    self.dynasty_id
                )

                if summary:
                    # Calculate committed cap (what actually counts in offseason = top-51)
                    total_cap_available = summary['salary_cap_limit'] + summary.get('carryover_from_previous', 0)
                    committed_cap = total_cap_available - cap_space

                    teams_data.append({
                        'team_id': team_id,
                        'cap_limit': summary['salary_cap_limit'],
                        'committed': committed_cap,
                        'available': cap_space,
                        'dead_money': summary['dead_money_total'],
                        'compliant': cap_space >= 0
                    })
            except Exception as e:
                print(f"Warning: Could not load data for team {team_id}: {e}")

        # Display teams
        for team_data in teams_data:
            team_name = self.formatter.format_team_name(team_data['team_id'])
            status = f"{self.formatter.STATUS_COMPLIANT} OK" if team_data['compliant'] else f"{self.formatter.STATUS_OVER_CAP} OVER"

            row = [
                team_name,
                format_currency(team_data['cap_limit']),
                format_currency(team_data['committed']),
                format_currency(team_data['available']),
                format_currency(team_data['dead_money']),
                status
            ]

            print(self.formatter.format_table_row(row, widths))

        # Bottom border
        print("└" + "─" * (sum(widths) + len(widths) * 3 - 1) + "┘")

        # Summary statistics
        total_available = sum(t['available'] for t in teams_data)
        compliant_count = sum(1 for t in teams_data if t['compliant'])

        print(f"\n📊 League Summary:")
        print(f"   Total Available Cap Space: {format_currency(total_available)}")
        print(f"   Compliant Teams: {compliant_count}/32 ({compliant_count/32*100:.1f}%)")
        print(f"   Non-Compliant Teams: {32 - compliant_count}")

    def show_team_details(self) -> None:
        """
        Display detailed cap breakdown for a specific team.

        Shows top contracts, cap breakdown, and roster composition.
        """
        print("\n" + "=" * 80)
        team_id_input = input("Enter team ID (1-32): ").strip()

        try:
            team_id = int(team_id_input)
            if team_id < 1 or team_id > 32:
                print("❌ Invalid team ID. Must be between 1 and 32.")
                return
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
            return

        team_name = self.formatter.format_team_name(team_id)
        print(f"\n{self.formatter.format_header(f'{team_name} - SALARY CAP DETAILS', 80)}\n")

        # Get cap summary
        summary = self.db_api.get_team_cap_summary(
            team_id,
            self.current_season,
            self.dynasty_id
        )

        if not summary:
            print(f"❌ No cap data found for {team_name}")
            return

        # Display cap summary
        print(format_cap_summary(summary))

        # Get team contracts
        contracts = self.db_api.get_team_contracts(
            team_id,
            self.current_season,
            self.dynasty_id,
            active_only=True
        )

        if contracts:
            print(f"\n📋 Active Contracts: {len(contracts)}")
            print("\nTop 10 Contracts by Total Value:")
            print("─" * 80)

            # Sort by total value
            top_contracts = sorted(contracts, key=lambda x: x['total_value'], reverse=True)[:10]

            for i, contract in enumerate(top_contracts, 1):
                years = contract['contract_years']
                total = format_currency(contract['total_value'])
                avg_per_year = format_currency(contract['total_value'] // years)
                guaranteed = format_currency(contract['total_guaranteed'])

                print(f"{i:2}. Player #{contract['player_id']:<5} | {years}yr | Total: {total:>15} | "
                      f"APY: {avg_per_year:>15} | Gtd: {guaranteed:>15}")
        else:
            print("\n📋 No active contracts found for this team.")

    def show_top_cap_hits(self) -> None:
        """
        Display league-wide top 10 highest cap hits.

        Shows player contracts with highest single-season cap impacts.
        """
        print(f"\n{self.formatter.format_header('TOP 10 HIGHEST CAP HITS - 2025', 100)}\n")

        # Collect all contracts across all teams
        all_contracts = []

        for team_id in range(1, 33):
            contracts = self.db_api.get_team_contracts(
                team_id,
                self.current_season,
                self.dynasty_id,
                active_only=True
            )

            for contract in contracts:
                # Get current year cap hit
                year_details = self.db_api.get_contract_year_details(
                    contract['contract_id'],
                    season_year=self.current_season
                )

                if year_details:
                    cap_hit = year_details[0]['total_cap_hit']
                    all_contracts.append({
                        'team_id': team_id,
                        'player_id': contract['player_id'],
                        'cap_hit': cap_hit,
                        'total_value': contract['total_value'],
                        'years': contract['contract_years']
                    })

        # Sort by cap hit
        top_contracts = sorted(all_contracts, key=lambda x: x['cap_hit'], reverse=True)[:10]

        if not top_contracts:
            print("❌ No contracts found in database.")
            return

        # Display table
        widths = [5, 25, 12, 18, 18, 8]
        headers = ["Rank", "Team", "Player", "Cap Hit", "Total Value", "Years"]

        print("┌" + "─" * (sum(widths) + len(widths) * 3 - 1) + "┐")
        print(self.formatter.format_table_row(headers, widths))
        print(self.formatter.format_separator(widths, "├", "┼", "┤", "─"))

        for i, contract in enumerate(top_contracts, 1):
            team_name = self.formatter.format_team_name(contract['team_id'])
            row = [
                str(i),
                team_name,
                f"Player {contract['player_id']}",
                format_currency(contract['cap_hit']),
                format_currency(contract['total_value']),
                str(contract['years'])
            ]
            print(self.formatter.format_table_row(row, widths))

        print("└" + "─" * (sum(widths) + len(widths) * 3 - 1) + "┘")

    def show_teams_by_cap_space(self) -> None:
        """
        Display teams ranked by available cap space (highest to lowest).

        Shows which teams have most/least financial flexibility.
        """
        print(f"\n{self.formatter.format_header('TEAMS RANKED BY AVAILABLE CAP SPACE', 100)}\n")

        # Collect cap space for all teams
        teams_data = []

        for team_id in range(1, 33):
            try:
                cap_space = self.calculator.calculate_team_cap_space(
                    team_id,
                    self.current_season,
                    self.dynasty_id,
                    roster_mode="offseason"
                )

                summary = self.db_api.get_team_cap_summary(
                    team_id,
                    self.current_season,
                    self.dynasty_id
                )

                if summary:
                    teams_data.append({
                        'team_id': team_id,
                        'cap_space': cap_space,
                        'cap_limit': summary['salary_cap_limit'],
                        'committed': summary['total_cap_used']
                    })
            except Exception:
                pass

        # Sort by cap space (descending)
        teams_data.sort(key=lambda x: x['cap_space'], reverse=True)

        # Display table
        widths = [5, 25, 18, 18, 18]
        headers = ["Rank", "Team", "Available", "Cap Limit", "Committed"]

        print("┌" + "─" * (sum(widths) + len(widths) * 3 - 1) + "┐")
        print(self.formatter.format_table_row(headers, widths))
        print(self.formatter.format_separator(widths, "├", "┼", "┤", "─"))

        for i, team in enumerate(teams_data, 1):
            team_name = self.formatter.format_team_name(team['team_id'])
            row = [
                str(i),
                team_name,
                format_currency(team['cap_space']),
                format_currency(team['cap_limit']),
                format_currency(team['committed'])
            ]
            print(self.formatter.format_table_row(row, widths))

        print("└" + "─" * (sum(widths) + len(widths) * 3 - 1) + "┘")

        # Highlight extremes
        print(f"\n🏆 Most Cap Space: {self.formatter.format_team_name(teams_data[0]['team_id'])} "
              f"- {format_currency(teams_data[0]['cap_space'])}")
        print(f"⚠️  Least Cap Space: {self.formatter.format_team_name(teams_data[-1]['team_id'])} "
              f"- {format_currency(teams_data[-1]['cap_space'])}")

    def test_player_release(self) -> None:
        """
        Test dead money calculation for player release.

        Interactive calculator for demonstrating cap impact of cutting a player.
        """
        print(f"\n{self.formatter.format_header('DEAD MONEY CALCULATOR - PLAYER RELEASE', 80)}\n")

        print("This calculator shows the dead money impact of releasing a player.")
        print("For demo purposes, we'll use hypothetical contract values.\n")

        try:
            # Get inputs
            remaining_proration_input = input("Enter remaining signing bonus proration ($): ").strip().replace(",", "")
            guaranteed_salary_input = input("Enter guaranteed salary ($): ").strip().replace(",", "")
            annual_proration_input = input("Enter annual proration amount ($): ").strip().replace(",", "")
            june_1_input = input("Use June 1 designation? (y/n): ").strip().lower()

            remaining_proration = int(remaining_proration_input)
            guaranteed_salary = int(guaranteed_salary_input)
            annual_proration = int(annual_proration_input)
            june_1 = june_1_input == 'y'

            # Calculate dead money
            current_year, next_year = self.calculator.calculate_dead_money_from_values(
                remaining_proration,
                guaranteed_salary,
                annual_proration,
                june_1
            )

            total_dead = current_year + next_year

            # Display results
            print("\n" + "=" * 80)
            print("DEAD MONEY CALCULATION RESULTS")
            print("=" * 80)
            print(f"\nRemaining Bonus Proration: {format_currency(remaining_proration)}")
            print(f"Guaranteed Salary:         {format_currency(guaranteed_salary)}")
            print(f"June 1 Designation:        {'Yes' if june_1 else 'No'}")
            print(f"\n{'-' * 80}")
            print(f"Current Year Dead Money:   {format_currency(current_year)}")
            print(f"Next Year Dead Money:      {format_currency(next_year)}")
            print(f"{'-' * 80}")
            print(f"TOTAL DEAD MONEY:          {format_currency(total_dead)}")
            print("=" * 80)

            if june_1:
                print(f"\n💡 With June 1 designation, dead money is split over 2 years:")
                print(f"   {self.current_season}: {format_currency(current_year)}")
                print(f"   {self.current_season + 1}: {format_currency(next_year)}")
            else:
                print(f"\n💡 Without June 1 designation, all dead money hits {self.current_season}: {format_currency(total_dead)}")

        except ValueError:
            print("\n❌ Invalid input. Please enter numeric values only.")
        except Exception as e:
            print(f"\n❌ Error calculating dead money: {e}")

    def test_contract_restructure(self) -> None:
        """
        Test contract restructure calculation.

        Interactive calculator for demonstrating cap savings from restructuring.
        """
        print(f"\n{self.formatter.format_header('CONTRACT RESTRUCTURE CALCULATOR', 80)}\n")

        print("Convert base salary to signing bonus to create immediate cap relief.")
        print("Shows current year savings and future year impacts.\n")

        try:
            # Get inputs
            base_salary_input = input("Enter base salary to convert ($): ").strip().replace(",", "")
            remaining_years_input = input("Enter remaining contract years: ").strip()

            base_salary = int(base_salary_input)
            remaining_years = int(remaining_years_input)

            # Calculate restructure impact
            result = self.calculator.calculate_restructure_impact(
                base_salary,
                remaining_years
            )

            # Display results
            print("\n" + "=" * 80)
            print("CONTRACT RESTRUCTURE RESULTS")
            print("=" * 80)
            print(f"\nBase Salary to Convert:    {format_currency(base_salary)}")
            print(f"Remaining Contract Years:  {remaining_years}")
            print(f"\n{'-' * 80}")
            print(f"New Annual Proration:      {format_currency(result['new_proration'])}")
            print(f"\n{'-' * 80}")
            print(f"✓ Current Year Savings:    {format_currency(result['cap_savings_current_year'])} (GREEN)")
            print(f"✗ Future Year Increase:    {format_currency(result['annual_increase_future_years'])} per year (RED)")
            print(f"⚠ Dead Money Increase:     {format_currency(result['dead_money_increase'])} if cut later (YELLOW)")
            print("=" * 80)

            print(f"\n💡 Restructure Summary:")
            print(f"   Immediate cap relief of {format_currency(result['cap_savings_current_year'])} in {self.current_season}")
            print(f"   But adds {format_currency(result['annual_increase_future_years'])} to each of next {remaining_years - 1} years")
            print(f"   Future dead money risk increases by {format_currency(result['dead_money_increase'])}")

        except ValueError:
            print("\n❌ Invalid input. Please enter numeric values.")
        except Exception as e:
            print(f"\n❌ Error calculating restructure: {e}")

    def validate_team_compliance(self) -> None:
        """
        Validate cap compliance for all teams or specific team.

        Shows which teams are cap-compliant and which are over.
        """
        print(f"\n{self.formatter.format_header('SALARY CAP COMPLIANCE VALIDATION', 80)}\n")

        choice = input("Validate (1) All Teams or (2) Specific Team? Enter 1 or 2: ").strip()

        if choice == "1":
            # All teams
            print("\nValidating cap compliance for all 32 teams...\n")

            compliant_teams = []
            non_compliant_teams = []

            for team_id in range(1, 33):
                try:
                    is_compliant, message = self.calculator.check_cap_compliance(
                        team_id,
                        self.current_season,
                        self.dynasty_id
                    )

                    team_name = self.formatter.format_team_name(team_id)

                    if is_compliant:
                        compliant_teams.append((team_name, message))
                    else:
                        non_compliant_teams.append((team_name, message))

                except Exception as e:
                    print(f"⚠ Warning: Could not validate {self.formatter.format_team_name(team_id)}: {e}")

            # Display results
            print("=" * 80)
            print(f"COMPLIANCE SUMMARY - {self.current_season} Season")
            print("=" * 80)
            print(f"\n✓ COMPLIANT TEAMS: {len(compliant_teams)}/32")
            print(f"✗ NON-COMPLIANT TEAMS: {len(non_compliant_teams)}/32")
            print(f"\nCompliance Rate: {len(compliant_teams)/32*100:.1f}%")

            if non_compliant_teams:
                print("\n" + "-" * 80)
                print("NON-COMPLIANT TEAMS (Action Required):")
                print("-" * 80)
                for team_name, message in non_compliant_teams:
                    print(f"✗ {team_name}: {message}")

            print("\n" + "=" * 80)

        elif choice == "2":
            # Specific team
            team_id_input = input("\nEnter team ID (1-32): ").strip()

            try:
                team_id = int(team_id_input)
                if team_id < 1 or team_id > 32:
                    print("❌ Invalid team ID. Must be between 1 and 32.")
                    return

                team_name = self.formatter.format_team_name(team_id)
                is_compliant, message = self.calculator.check_cap_compliance(
                    team_id,
                    self.current_season,
                    self.dynasty_id
                )

                print("\n" + "=" * 80)
                print(f"COMPLIANCE CHECK - {team_name}")
                print("=" * 80)

                if is_compliant:
                    print(f"\n✓ STATUS: COMPLIANT")
                    print(f"   {message}")
                else:
                    print(f"\n✗ STATUS: NON-COMPLIANT")
                    print(f"   {message}")
                    print(f"\n⚠ Action Required: Team must cut players or restructure contracts.")

                print("=" * 80)

            except ValueError:
                print("\n❌ Invalid input. Please enter a number.")
            except Exception as e:
                print(f"\n❌ Error checking compliance: {e}")

        else:
            print("\n❌ Invalid choice. Please enter 1 or 2.")

    def show_database_stats(self) -> None:
        """
        Display database statistics and summary information.

        Shows total contracts, total cap committed, average per team, etc.
        """
        print(f"\n{self.formatter.format_header('DATABASE STATISTICS', 80)}\n")

        try:
            # Count total contracts
            total_contracts = 0
            total_contract_value = 0
            total_cap_committed = 0
            total_dead_money = 0

            for team_id in range(1, 33):
                contracts = self.db_api.get_team_contracts(
                    team_id,
                    self.current_season,
                    self.dynasty_id,
                    active_only=True
                )

                total_contracts += len(contracts)
                total_contract_value += sum(c['total_value'] for c in contracts)

                summary = self.db_api.get_team_cap_summary(
                    team_id,
                    self.current_season,
                    self.dynasty_id
                )

                if summary:
                    total_cap_committed += summary['total_cap_used']
                    total_dead_money += summary['dead_money_total']

            # Display statistics
            print("=" * 80)
            print("DATABASE OVERVIEW")
            print("=" * 80)
            print(f"\nDynasty ID:            {self.dynasty_id}")
            print(f"Current Season:        {self.current_season}")
            print(f"\n{'-' * 80}")
            print("CONTRACT STATISTICS:")
            print(f"   Total Active Contracts:    {total_contracts}")
            print(f"   Total Contract Value:      {format_currency(total_contract_value)}")
            print(f"   Average Contracts/Team:    {total_contracts / 32:.1f}")
            print(f"\n{'-' * 80}")
            print("CAP STATISTICS:")
            print(f"   Total Cap Committed:       {format_currency(total_cap_committed)}")
            print(f"   Average Cap/Team:          {format_currency(total_cap_committed // 32)}")
            print(f"   Total Dead Money:          {format_currency(total_dead_money)}")
            print(f"   Average Dead Money/Team:   {format_currency(total_dead_money // 32)}")
            print("=" * 80)

            # Additional insights
            avg_contract_value = total_contract_value // total_contracts if total_contracts > 0 else 0
            print(f"\n📊 Insights:")
            print(f"   Average Contract Value: {format_currency(avg_contract_value)}")
            print(f"   League-Wide Cap Utilization: {(total_cap_committed / (255_000_000 * 32)) * 100:.1f}%")

        except Exception as e:
            print(f"\n❌ Error retrieving database statistics: {e}")


def main():
    """
    Main entry point for the Salary Cap Calculator Demo.
    """
    print("\n" + "=" * 80)
    print("NFL SALARY CAP CALCULATOR - INTERACTIVE DEMO")
    print("=" * 80)
    print("\nInitializing demo database with sample cap data...")

    try:
        app = CapDemoApp()
        print("✓ Initialization complete!\n")
        app.run()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
