"""
Load Player Contracts Script

Loads all player contracts from team JSON files into the cap demo database.
Processes all 32 NFL teams and creates detailed contract structures.

Features:
- Reads all team player files from src/data/players/team_*.json
- Generates detailed contract structures for each player
- Inserts contracts and year-by-year details into database
- Tracks statistics and displays progress
- Graceful error handling
"""

import json
import glob
import sys
from pathlib import Path
from datetime import date
from typing import Dict, Any, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from salary_cap.cap_database_api import CapDatabaseAPI
from constants.team_ids import TeamIDs


class ContractGenerator:
    """
    Generates detailed contract structures from basic contract data.

    Takes simple contract info (years, salary, bonuses) and creates
    comprehensive year-by-year breakdowns with cap hits and cash flows.
    """

    @staticmethod
    def generate_contract_details(
        player_id: int,
        team_id: int,
        contract_data: Dict[str, Any],
        current_season: int = 2025
    ) -> Dict[str, Any]:
        """
        Generate detailed contract structure from basic contract data.

        Args:
            player_id: Player ID
            team_id: Team ID
            contract_data: Contract data from player JSON
            current_season: Current season year

        Returns:
            Dict with contract details and year breakdowns
        """
        # Extract basic contract info
        contract_years = contract_data.get('contract_years', 1)
        annual_salary = contract_data.get('annual_salary', 1000000)
        signing_bonus = contract_data.get('signing_bonus', 0)
        guaranteed_money = contract_data.get('guaranteed_money', 0)

        # Map contract type to valid values
        raw_contract_type = contract_data.get('contract_type', 'veteran').lower()
        contract_type_map = {
            'rookie': 'ROOKIE',
            'veteran': 'VETERAN',
            'extension': 'EXTENSION',
            'franchise_tag': 'FRANCHISE_TAG',
            'transition_tag': 'TRANSITION_TAG'
        }
        contract_type = contract_type_map.get(raw_contract_type, 'VETERAN')

        # Calculate total value
        total_value = (annual_salary * contract_years) + signing_bonus

        # Signing bonus proration (spread over contract years, max 5 years)
        proration_years = min(contract_years, 5)
        signing_bonus_proration = signing_bonus // proration_years if proration_years > 0 else 0

        # Start and end years
        start_year = current_season
        end_year = current_season + contract_years - 1

        # Calculate guaranteed at signing (typically front-loaded)
        guaranteed_at_signing = min(guaranteed_money, total_value // 2)

        # Generate year-by-year details
        year_details = []
        remaining_guaranteed = guaranteed_money

        for year_num in range(1, contract_years + 1):
            season_year = start_year + year_num - 1

            # Base salary typically escalates slightly each year
            escalation_factor = 1.0 + (0.05 * (year_num - 1))  # 5% per year
            base_salary = int(annual_salary * escalation_factor)

            # Determine if this year's base salary is guaranteed
            base_salary_guaranteed = remaining_guaranteed >= base_salary
            if base_salary_guaranteed:
                remaining_guaranteed -= base_salary
                guarantee_type = "FULL"
            elif remaining_guaranteed > 0:
                guarantee_type = "SKILL"  # Partial guarantees are typically skill-based
                remaining_guaranteed = 0
            else:
                guarantee_type = None

            # Calculate cap hit components
            roster_bonus = 0  # Simplified - no roster bonuses
            workout_bonus = 0
            option_bonus = 0

            # Signing bonus proration (for applicable years)
            year_signing_bonus_proration = signing_bonus_proration if year_num <= proration_years else 0

            # Total cap hit
            total_cap_hit = (
                base_salary +
                roster_bonus +
                workout_bonus +
                year_signing_bonus_proration
            )

            # Cash paid this year
            cash_paid = base_salary + roster_bonus + workout_bonus
            if year_num == 1:
                cash_paid += signing_bonus  # Signing bonus paid upfront

            year_details.append({
                'contract_year': year_num,
                'season_year': season_year,
                'base_salary': base_salary,
                'roster_bonus': roster_bonus,
                'workout_bonus': workout_bonus,
                'option_bonus': option_bonus,
                'signing_bonus_proration': year_signing_bonus_proration,
                'total_cap_hit': total_cap_hit,
                'cash_paid': cash_paid,
                'base_salary_guaranteed': base_salary_guaranteed,
                'guarantee_type': guarantee_type,
                'guarantee_date': date(season_year, 3, 1) if base_salary_guaranteed else None
            })

        return {
            'contract': {
                'player_id': player_id,
                'team_id': team_id,
                'start_year': start_year,
                'end_year': end_year,
                'contract_years': contract_years,
                'contract_type': contract_type,
                'total_value': total_value,
                'signing_bonus': signing_bonus,
                'signing_bonus_proration': signing_bonus_proration,
                'guaranteed_at_signing': guaranteed_at_signing,
                'injury_guaranteed': 0,  # Simplified
                'total_guaranteed': guaranteed_money,
                'signed_date': date(current_season, 3, 15)  # Typical free agency date
            },
            'year_details': year_details
        }


class ContractLoader:
    """Loads player contracts from team files into database."""

    def __init__(self, database_path: str = "demo/cap_calculator_demo/cap_demo.db"):
        """
        Initialize contract loader.

        Args:
            database_path: Path to database file
        """
        self.database_path = database_path
        self.api = CapDatabaseAPI(database_path)
        self.dynasty_id = "cap_demo_dynasty"
        self.current_season = 2025

        # Statistics tracking
        self.stats = {
            'teams_processed': 0,
            'players_loaded': 0,
            'contracts_created': 0,
            'players_skipped': 0,
            'errors': 0
        }

        # Track cap commitment by team
        self.team_cap_commitments: Dict[int, int] = {}
        self.team_names: Dict[int, str] = {}

    def load_all_contracts(self) -> None:
        """Load contracts from all team files."""
        print("LOADING PLAYER CONTRACTS")
        print("=" * 60)
        print(f"Database: {self.database_path}")
        print(f"Dynasty: {self.dynasty_id}")
        print(f"Season: {self.current_season}")
        print()

        # Get all team player files
        player_files = sorted(glob.glob("src/data/players/team_*.json"))

        if not player_files:
            print("ERROR: No team player files found!")
            return

        print(f"Found {len(player_files)} team files\n")

        # Process each team
        for file_path in player_files:
            self._process_team_file(file_path)

        # Display summary
        self._display_summary()

    def _process_team_file(self, file_path: str) -> None:
        """
        Process a single team file.

        Args:
            file_path: Path to team JSON file
        """
        try:
            with open(file_path, 'r') as f:
                team_data = json.load(f)

            # Extract team info - handle two formats
            # Format 1: {team_info: {team_id, team_name, ...}, players: {...}}
            # Format 2: {team_id, team_name, players: {...}}
            if 'team_info' in team_data:
                team_info = team_data['team_info']
                team_id = team_info.get('team_id')
                team_name = team_info.get('team_name', 'Unknown Team')
            else:
                team_id = team_data.get('team_id')
                team_name = team_data.get('team_name', 'Unknown Team')

            if not team_id:
                print(f"SKIPPED: {file_path} (missing team_id)")
                return

            # Store team name for summary
            self.team_names[team_id] = team_name

            # Process players
            players = team_data.get('players', {})
            contracts_loaded = 0
            players_processed = 0

            for player_data in players.values():
                if self._process_player(player_data, team_id):
                    contracts_loaded += 1
                players_processed += 1

            # Update statistics
            self.stats['teams_processed'] += 1
            self.stats['players_loaded'] += players_processed

            print(f"Processing {team_name}... ({players_processed} players, {contracts_loaded} contracts)")

        except Exception as e:
            print(f"ERROR processing {file_path}: {e}")
            self.stats['errors'] += 1

    def _process_player(self, player_data: Dict[str, Any], team_id: int) -> bool:
        """
        Process a single player and create contract.

        Args:
            player_data: Player data dict
            team_id: Team ID

        Returns:
            True if contract created, False if skipped
        """
        try:
            player_id = player_data.get('player_id')
            contract_data = player_data.get('contract')

            # Skip if no contract data
            if not contract_data or not player_id:
                self.stats['players_skipped'] += 1
                return False

            # Generate detailed contract structure
            contract_details = ContractGenerator.generate_contract_details(
                player_id=player_id,
                team_id=team_id,
                contract_data=contract_data,
                current_season=self.current_season
            )

            # Insert contract
            contract_info = contract_details['contract']
            contract_id = self.api.insert_contract(
                player_id=contract_info['player_id'],
                team_id=contract_info['team_id'],
                dynasty_id=self.dynasty_id,
                start_year=contract_info['start_year'],
                end_year=contract_info['end_year'],
                contract_years=contract_info['contract_years'],
                contract_type=contract_info['contract_type'],
                total_value=contract_info['total_value'],
                signing_bonus=contract_info['signing_bonus'],
                signing_bonus_proration=contract_info['signing_bonus_proration'],
                guaranteed_at_signing=contract_info['guaranteed_at_signing'],
                injury_guaranteed=contract_info['injury_guaranteed'],
                total_guaranteed=contract_info['total_guaranteed'],
                signed_date=contract_info['signed_date']
            )

            # Insert year details
            for year_detail in contract_details['year_details']:
                self.api.insert_contract_year_details(
                    contract_id=contract_id,
                    contract_year=year_detail['contract_year'],
                    season_year=year_detail['season_year'],
                    base_salary=year_detail['base_salary'],
                    total_cap_hit=year_detail['total_cap_hit'],
                    cash_paid=year_detail['cash_paid'],
                    roster_bonus=year_detail['roster_bonus'],
                    workout_bonus=year_detail['workout_bonus'],
                    option_bonus=year_detail['option_bonus'],
                    base_salary_guaranteed=year_detail['base_salary_guaranteed'],
                    guarantee_type=year_detail['guarantee_type'],
                    guarantee_date=year_detail['guarantee_date'],
                    signing_bonus_proration=year_detail['signing_bonus_proration']
                )

            # Track cap commitment for current year
            current_year_cap = next(
                (yd['total_cap_hit'] for yd in contract_details['year_details']
                 if yd['season_year'] == self.current_season),
                0
            )

            if team_id not in self.team_cap_commitments:
                self.team_cap_commitments[team_id] = 0
            self.team_cap_commitments[team_id] += current_year_cap

            self.stats['contracts_created'] += 1
            return True

        except Exception as e:
            print(f"  ERROR processing player {player_data.get('player_id', 'unknown')}: {e}")
            self.stats['errors'] += 1
            return False

    def _display_summary(self) -> None:
        """Display loading summary with statistics."""
        print()
        print("LOAD COMPLETE")
        print("=" * 60)
        print(f"Teams Processed:     {self.stats['teams_processed']:,}")
        print(f"Players Loaded:      {self.stats['players_loaded']:,}")
        print(f"Contracts Created:   {self.stats['contracts_created']:,}")
        print(f"Players Skipped:     {self.stats['players_skipped']:,}")
        print(f"Errors:              {self.stats['errors']:,}")
        print()

        # Display top 3 teams by cap commitment
        if self.team_cap_commitments:
            print("Top 3 Teams by Cap Commitment:")
            sorted_teams = sorted(
                self.team_cap_commitments.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            for rank, (team_id, cap_total) in enumerate(sorted_teams, 1):
                team_name = self.team_names.get(team_id, f"Team {team_id}")
                cap_millions = cap_total / 1_000_000
                print(f"{rank}. {team_name}: ${cap_millions:.1f}M")

        print()
        print(f"Database: {self.database_path}")
        print("Ready for cap calculations!")


def main():
    """Main entry point."""
    loader = ContractLoader()
    loader.load_all_contracts()


if __name__ == "__main__":
    main()
