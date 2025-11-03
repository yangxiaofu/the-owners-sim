"""
Contract Initializer for The Owner's Sim

Converts JSON contract data to NFL salary cap database format during dynasty initialization.
Handles contract creation, signing bonus proration, and year-by-year breakdown.
"""

from typing import Dict, List, Any, Optional
import sqlite3
import logging


class ContractInitializer:
    """
    Initializes player contracts from JSON data during dynasty creation.

    Responsibilities:
    - Convert JSON contract format → database schema
    - Create player_contracts records
    - Generate contract_year_details for each year
    - Calculate signing bonus proration
    - Link contracts to players via contract_id
    """

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize contract initializer.

        Args:
            connection: Shared database connection (must be in transaction mode)
        """
        self.conn = connection
        self.logger = logging.getLogger("ContractInitializer")

    def initialize_contracts_from_json(
        self,
        dynasty_id: str,
        season: int,
        players_with_contracts: List[Dict[str, Any]]
    ) -> Dict[int, int]:
        """
        Create contracts for all players from JSON data.

        Args:
            dynasty_id: Dynasty identifier
            season: Starting season year (e.g., 2025)
            players_with_contracts: List of dicts with keys:
                - player_id: Database player_id (int)
                - team_id: Team ID (1-32)
                - contract: Dict from JSON with contract details

        Returns:
            Dict mapping player_id → contract_id for all created contracts

        Example JSON contract format:
        {
            "contract_years": 4,
            "annual_salary": 53000000,
            "signing_bonus": 73000000,
            "guaranteed_money": 170000000,
            "contract_type": "extension",
            "cap_hit_2025": 32600000
        }
        """
        contract_id_map = {}
        contracts_created = 0

        try:
            for player_data in players_with_contracts:
                player_id = player_data['player_id']
                team_id = player_data['team_id']
                json_contract = player_data.get('contract')

                # Defensive validation: Verify team_id consistency
                # This prevents contract/player team_id mismatches that break trade validation
                if not isinstance(team_id, int) or team_id < 1 or team_id > 32:
                    raise ValueError(
                        f"Invalid team_id={team_id} for player_id={player_id}. "
                        f"Expected integer 1-32. This indicates a bug in player roster initialization."
                    )

                # Skip players without contract data
                if not json_contract:
                    self.logger.warning(f"Player {player_id} has no contract data, skipping")
                    continue

                # Create contract and get contract_id
                contract_id = self._create_contract(
                    dynasty_id=dynasty_id,
                    player_id=player_id,
                    team_id=team_id,
                    season=season,
                    json_contract=json_contract
                )

                contract_id_map[player_id] = contract_id
                contracts_created += 1

            self.logger.info(f"✅ Created {contracts_created} contracts for dynasty '{dynasty_id}'")
            return contract_id_map

        except Exception as e:
            self.logger.error(f"Contract initialization failed: {e}")
            raise

    def _create_contract(
        self,
        dynasty_id: str,
        player_id: int,
        team_id: int,
        season: int,
        json_contract: Dict[str, Any]
    ) -> int:
        """
        Create single contract from JSON data.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player database ID
            team_id: Team ID (1-32)
            season: Starting season year
            json_contract: Contract dict from JSON

        Returns:
            contract_id of created contract
        """
        # Extract JSON contract fields
        contract_years = json_contract.get('contract_years', 1)
        annual_salary = json_contract.get('annual_salary', 0)
        signing_bonus = json_contract.get('signing_bonus', 0)
        guaranteed_money = json_contract.get('guaranteed_money', 0)
        contract_type = json_contract.get('contract_type', 'veteran').upper()
        cap_hit_2025 = json_contract.get('cap_hit_2025', 0)

        # Calculate contract duration
        start_year = season
        end_year = season + contract_years - 1
        total_value = annual_salary * contract_years

        # Calculate signing bonus proration (spread evenly across years, max 5 years per NFL rules)
        proration_years = min(contract_years, 5)
        signing_bonus_proration = signing_bonus // proration_years if signing_bonus > 0 else 0

        # Map JSON contract_type to database enum
        db_contract_type = self._map_contract_type(contract_type)

        # Insert into player_contracts table
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO player_contracts (
                player_id, team_id, dynasty_id,
                start_year, end_year, contract_years,
                contract_type,
                total_value, signing_bonus, signing_bonus_proration,
                guaranteed_at_signing, total_guaranteed,
                is_active, signed_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
        ''', (
            player_id, team_id, dynasty_id,
            start_year, end_year, contract_years,
            db_contract_type,
            total_value, signing_bonus, signing_bonus_proration,
            guaranteed_money, guaranteed_money,
            f"{season}-03-01"  # Approximate signing date (March 1 of season)
        ))

        contract_id = cursor.lastrowid

        # Create year-by-year contract details
        self._create_contract_year_details(
            cursor=cursor,
            contract_id=contract_id,
            start_year=start_year,
            contract_years=contract_years,
            annual_salary=annual_salary,
            signing_bonus_proration=signing_bonus_proration,
            cap_hit_2025=cap_hit_2025
        )

        return contract_id

    def _create_contract_year_details(
        self,
        cursor: sqlite3.Cursor,
        contract_id: int,
        start_year: int,
        contract_years: int,
        annual_salary: int,
        signing_bonus_proration: int,
        cap_hit_2025: int
    ):
        """
        Create year-by-year contract breakdown.

        Args:
            cursor: Database cursor
            contract_id: Parent contract ID
            start_year: Contract start year (e.g., 2025)
            contract_years: Number of contract years
            annual_salary: Annual base salary
            signing_bonus_proration: Annual signing bonus proration
            cap_hit_2025: Known cap hit for first year (from JSON)
        """
        for year_num in range(1, contract_years + 1):
            season_year = start_year + year_num - 1

            # For first year, use known cap hit from JSON
            # For subsequent years, estimate as base salary + signing bonus proration
            if year_num == 1:
                total_cap_hit = cap_hit_2025
                # Back-calculate base salary from known cap hit
                base_salary = cap_hit_2025 - signing_bonus_proration
            else:
                base_salary = annual_salary
                total_cap_hit = base_salary + signing_bonus_proration

            # Cash paid = base salary + signing bonus proration
            cash_paid = base_salary + signing_bonus_proration

            cursor.execute('''
                INSERT INTO contract_year_details (
                    contract_id, contract_year, season_year,
                    base_salary,
                    signing_bonus_proration,
                    total_cap_hit,
                    cash_paid,
                    is_voided
                ) VALUES (?, ?, ?, ?, ?, ?, ?, FALSE)
            ''', (
                contract_id, year_num, season_year,
                base_salary,
                signing_bonus_proration,
                total_cap_hit,
                cash_paid
            ))

    def _map_contract_type(self, json_contract_type: str) -> str:
        """
        Map JSON contract_type to database enum.

        Args:
            json_contract_type: Contract type from JSON (lowercase)

        Returns:
            Database contract_type enum value (uppercase)

        Mapping:
            - rookie → ROOKIE
            - veteran → VETERAN
            - extension → EXTENSION
            - undrafted → VETERAN (treat as veteran minimum)
            - franchise_tag → FRANCHISE_TAG
            - transition_tag → TRANSITION_TAG
        """
        mapping = {
            'ROOKIE': 'ROOKIE',
            'VETERAN': 'VETERAN',
            'EXTENSION': 'EXTENSION',
            'UNDRAFTED': 'VETERAN',  # Treat UDFA as veteran minimum
            'FRANCHISE_TAG': 'FRANCHISE_TAG',
            'TRANSITION_TAG': 'TRANSITION_TAG'
        }

        return mapping.get(json_contract_type, 'VETERAN')

    def link_contracts_to_players(
        self,
        player_contract_map: Dict[int, int]
    ):
        """
        Update players table to link contract_id.

        Args:
            player_contract_map: Dict mapping player_id → contract_id
        """
        cursor = self.conn.cursor()

        for player_id, contract_id in player_contract_map.items():
            cursor.execute('''
                UPDATE players
                SET contract_id = ?
                WHERE player_id = ?
            ''', (contract_id, player_id))

        self.logger.info(f"✅ Linked {len(player_contract_map)} contracts to players")
