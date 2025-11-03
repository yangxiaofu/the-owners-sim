"""
Salary Cap Database API

Database interface for all salary cap operations including contracts,
cap tracking, franchise tags, dead money, and transaction logging.

Provides dynasty-aware CRUD operations for all cap-related tables.
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime
from pathlib import Path
import logging


class CapDatabaseAPI:
    """
    Database API for salary cap system.

    Handles all database operations for contracts, cap tracking,
    franchise tags, RFA tenders, dead money, and transactions.

    Features:
    - Dynasty isolation for all operations
    - Transaction logging
    - Optimized queries with indexes
    - Type-safe operations
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Cap Database API.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)

        # Ensure database directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema if needed
        self._ensure_schema_exists()

    def _ensure_schema_exists(self) -> None:
        """Ensure all salary cap tables exist."""
        migration_path = Path(__file__).parent.parent / "database" / "migrations" / "002_salary_cap_schema.sql"

        if not migration_path.exists():
            self.logger.warning(f"Migration file not found: {migration_path}")
            return

        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # Check if tables exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='player_contracts'"
                )
                if cursor.fetchone() is None:
                    # Run migration
                    with open(migration_path, 'r') as f:
                        migration_sql = f.read()
                    conn.executescript(migration_sql)
                    conn.commit()
                    self.logger.info("Salary cap schema initialized successfully")
        except Exception as e:
            self.logger.error(f"Error ensuring schema exists: {e}")
            raise

    # ========================================================================
    # CONTRACT OPERATIONS
    # ========================================================================

    def insert_contract(
        self,
        player_id: int,
        team_id: int,
        dynasty_id: str,
        start_year: int,
        end_year: int,
        contract_years: int,
        contract_type: str,
        total_value: int,
        signing_bonus: int = 0,
        signing_bonus_proration: int = 0,
        guaranteed_at_signing: int = 0,
        injury_guaranteed: int = 0,
        total_guaranteed: int = 0,
        signed_date: Optional[date] = None
    ) -> int:
        """
        Insert new player contract.

        Args:
            player_id: Player ID
            team_id: Team ID
            dynasty_id: Dynasty identifier
            start_year: Contract start year
            end_year: Contract end year
            contract_years: Total contract years
            contract_type: Type (ROOKIE, VETERAN, FRANCHISE_TAG, etc.)
            total_value: Total contract value in dollars
            signing_bonus: Signing bonus amount
            signing_bonus_proration: Annual proration amount
            guaranteed_at_signing: Money guaranteed at signing
            injury_guaranteed: Injury guarantee amount
            total_guaranteed: Total guaranteed money
            signed_date: Date contract was signed

        Returns:
            contract_id of newly created contract
        """
        if signed_date is None:
            signed_date = date.today()

        with sqlite3.connect(self.database_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.execute('''
                INSERT INTO player_contracts (
                    player_id, team_id, dynasty_id,
                    start_year, end_year, contract_years,
                    contract_type, total_value, signing_bonus, signing_bonus_proration,
                    guaranteed_at_signing, injury_guaranteed, total_guaranteed,
                    is_active, signed_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
            ''', (
                player_id, team_id, dynasty_id,
                start_year, end_year, contract_years,
                contract_type, total_value, signing_bonus, signing_bonus_proration,
                guaranteed_at_signing, injury_guaranteed, total_guaranteed,
                signed_date
            ))
            conn.commit()
            return cursor.lastrowid

    def insert_contract_year_details(
        self,
        contract_id: int,
        contract_year: int,
        season_year: int,
        base_salary: int,
        total_cap_hit: int,
        cash_paid: int,
        roster_bonus: int = 0,
        workout_bonus: int = 0,
        option_bonus: int = 0,
        per_game_roster_bonus: int = 0,
        ltbe_incentives: int = 0,
        nltbe_incentives: int = 0,
        base_salary_guaranteed: bool = False,
        guarantee_type: Optional[str] = None,
        guarantee_date: Optional[date] = None,
        signing_bonus_proration: int = 0,
        option_bonus_proration: int = 0,
        is_voided: bool = False
    ) -> int:
        """
        Insert contract year details.

        Args:
            contract_id: Parent contract ID
            contract_year: Year of contract (1-based)
            season_year: Absolute season year
            base_salary: Base salary for this year
            total_cap_hit: Total cap hit including all components
            cash_paid: Actual cash paid in this year
            (Additional bonus and incentive parameters...)

        Returns:
            detail_id of inserted record
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute('''
                INSERT INTO contract_year_details (
                    contract_id, contract_year, season_year,
                    base_salary, roster_bonus, workout_bonus, option_bonus, per_game_roster_bonus,
                    ltbe_incentives, nltbe_incentives,
                    base_salary_guaranteed, guarantee_type, guarantee_date,
                    signing_bonus_proration, option_bonus_proration,
                    total_cap_hit, cash_paid, is_voided
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                contract_id, contract_year, season_year,
                base_salary, roster_bonus, workout_bonus, option_bonus, per_game_roster_bonus,
                ltbe_incentives, nltbe_incentives,
                base_salary_guaranteed, guarantee_type, guarantee_date,
                signing_bonus_proration, option_bonus_proration,
                total_cap_hit, cash_paid, is_voided
            ))
            conn.commit()
            return cursor.lastrowid

    def get_contract(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve contract by ID.

        Args:
            contract_id: Contract ID

        Returns:
            Contract dict or None if not found
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM player_contracts WHERE contract_id = ?
            ''', (contract_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_team_contracts(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all contracts for a team in a given season.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            active_only: Only return active contracts

        Returns:
            List of contract dicts
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row

            query = '''
                SELECT * FROM player_contracts
                WHERE team_id = ?
                  AND dynasty_id = ?
                  AND start_year <= ?
                  AND end_year >= ?
            '''
            params = [team_id, dynasty_id, season, season]

            if active_only:
                query += " AND is_active = TRUE"

            query += " ORDER BY total_value DESC"

            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            return results

    def get_player_contract(
        self,
        player_id: str,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get active contract for a specific player on a specific team.

        Args:
            player_id: Player ID
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier for proper isolation

        Returns:
            Contract dict or None if not found
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute('''
                SELECT * FROM player_contracts
                WHERE player_id = ?
                  AND team_id = ?
                  AND dynasty_id = ?
                  AND start_year <= ?
                  AND end_year >= ?
                  AND is_active = TRUE
                LIMIT 1
            ''', (player_id, team_id, dynasty_id, season, season))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_contract_year_details(
        self,
        contract_id: int,
        season_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get year-by-year details for a contract.

        Args:
            contract_id: Contract ID
            season_year: Optional specific year to retrieve

        Returns:
            List of contract year detail dicts
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row

            query = '''
                SELECT * FROM contract_year_details
                WHERE contract_id = ?
            '''
            params = [contract_id]

            if season_year is not None:
                query += " AND season_year = ?"
                params.append(season_year)

            query += " ORDER BY contract_year"

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_expiring_contracts(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all contracts expiring after this season.

        Useful for identifying pending free agents who may need
        franchise tags or will enter free agency.

        Args:
            team_id: Team ID (1-32)
            season: Current season year (contracts ending this year)
            dynasty_id: Dynasty identifier
            active_only: Only return active contracts (default True)

        Returns:
            List of contract dicts with embedded player information

        Example:
            >>> api = CapDatabaseAPI()
            >>> expiring = api.get_expiring_contracts(
            ...     team_id=7,
            ...     season=2024,
            ...     dynasty_id="my_dynasty"
            ... )
            >>> print(f"Found {len(expiring)} expiring contracts")
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row

            query = '''
                SELECT
                    pc.*,
                    p.first_name || ' ' || p.last_name as player_name,
                    p.positions,
                    p.attributes,
                    p.years_pro,
                    p.birthdate
                FROM player_contracts pc
                JOIN players p
                    ON pc.player_id = p.player_id
                    AND pc.dynasty_id = p.dynasty_id
                WHERE pc.team_id = ?
                  AND pc.dynasty_id = ?
                  AND pc.end_year = ?
            '''
            params = [team_id, dynasty_id, season]

            if active_only:
                query += " AND pc.is_active = TRUE"

            query += " ORDER BY pc.total_value DESC"

            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            return results

    def get_pending_free_agents(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        min_overall: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get pending free agents (contracts expiring) filtered by quality.

        Convenience method that filters expiring contracts by player
        overall rating. Useful for franchise tag decisions and free
        agency planning.

        Args:
            team_id: Team ID (1-32)
            season: Current season year
            dynasty_id: Dynasty identifier
            min_overall: Minimum overall rating to include (0-100)

        Returns:
            List of simplified player dicts sorted by overall rating

        Example:
            >>> api = CapDatabaseAPI()
            >>> top_fas = api.get_pending_free_agents(
            ...     team_id=7,
            ...     season=2024,
            ...     dynasty_id="my_dynasty",
            ...     min_overall=80  # Only elite players
            ... )
            >>> for fa in top_fas:
            ...     print(f"{fa['player_name']} ({fa['position']}) - {fa['overall']} OVR")
        """
        # Get raw expiring contracts
        expiring = self.get_expiring_contracts(team_id, season, dynasty_id)

        # Parse and filter by overall rating
        pending_fas = []
        for contract in expiring:
            # Parse JSON attributes
            attrs = json.loads(contract['attributes'])
            overall = attrs.get('overall', 0)

            # Filter by minimum overall
            if overall >= min_overall:
                # Parse positions
                positions = json.loads(contract['positions'])
                primary_position = positions[0] if positions else 'UNKNOWN'

                # Build simplified dict
                pending_fas.append({
                    'player_id': contract['player_id'],
                    'player_name': contract['player_name'],
                    'position': primary_position,
                    'overall': overall,
                    'years_pro': contract['years_pro'],
                    'contract_id': contract['contract_id'],
                    'contract_value': contract['total_value'],
                    'contract_years': contract['contract_years'],
                    'aav': contract['total_value'] // contract['contract_years'] if contract['contract_years'] > 0 else 0
                })

        # Sort by overall rating (best players first)
        pending_fas.sort(key=lambda x: x['overall'], reverse=True)

        return pending_fas

    def void_contract(self, contract_id: int, void_date: Optional[date] = None) -> None:
        """
        Mark contract as voided.

        Args:
            contract_id: Contract ID to void
            void_date: Date contract voided
        """
        if void_date is None:
            void_date = date.today()

        with sqlite3.connect(self.database_path) as conn:
            conn.execute('''
                UPDATE player_contracts
                SET is_active = FALSE,
                    voided_date = ?,
                    modified_at = CURRENT_TIMESTAMP
                WHERE contract_id = ?
            ''', (void_date, contract_id))
            conn.commit()

    # ========================================================================
    # TEAM CAP OPERATIONS
    # ========================================================================

    def initialize_team_cap(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        salary_cap_limit: int,
        carryover_from_previous: int = 0
    ) -> int:
        """
        Initialize team salary cap for a season.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            salary_cap_limit: League-wide cap limit
            carryover_from_previous: Cap space carried over

        Returns:
            cap_id of inserted record
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute('''
                INSERT OR REPLACE INTO team_salary_cap (
                    team_id, season, dynasty_id,
                    salary_cap_limit, carryover_from_previous,
                    is_top_51_active
                ) VALUES (?, ?, ?, ?, ?, TRUE)
            ''', (team_id, season, dynasty_id, salary_cap_limit, carryover_from_previous))
            conn.commit()
            return cursor.lastrowid

    def update_team_cap(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        active_contracts_total: Optional[int] = None,
        dead_money_total: Optional[int] = None,
        ltbe_incentives_total: Optional[int] = None,
        practice_squad_total: Optional[int] = None,
        top_51_total: Optional[int] = None,
        cash_spent_this_year: Optional[int] = None,
        is_top_51_active: Optional[bool] = None
    ) -> None:
        """
        Update team cap totals.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            active_contracts_total: Total of active contracts
            dead_money_total: Total dead money
            ltbe_incentives_total: Total LTBE incentives
            practice_squad_total: Total practice squad cost
            top_51_total: Total of top 51 contracts (offseason)
            cash_spent_this_year: Cash spending for floor calculation
            is_top_51_active: Whether top-51 rule is active
        """
        updates = []
        params = []

        if active_contracts_total is not None:
            updates.append("active_contracts_total = ?")
            params.append(active_contracts_total)

        if dead_money_total is not None:
            updates.append("dead_money_total = ?")
            params.append(dead_money_total)

        if ltbe_incentives_total is not None:
            updates.append("ltbe_incentives_total = ?")
            params.append(ltbe_incentives_total)

        if practice_squad_total is not None:
            updates.append("practice_squad_total = ?")
            params.append(practice_squad_total)

        if top_51_total is not None:
            updates.append("top_51_total = ?")
            params.append(top_51_total)

        if cash_spent_this_year is not None:
            updates.append("cash_spent_this_year = ?")
            params.append(cash_spent_this_year)

        if is_top_51_active is not None:
            updates.append("is_top_51_active = ?")
            params.append(is_top_51_active)

        if not updates:
            return

        updates.append("last_updated = CURRENT_TIMESTAMP")
        params.extend([team_id, season, dynasty_id])

        query = f'''
            UPDATE team_salary_cap
            SET {', '.join(updates)}
            WHERE team_id = ? AND season = ? AND dynasty_id = ?
        '''

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(query, params)
            conn.commit()

    def get_team_cap_summary(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete cap summary for a team.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Cap summary dict with all totals and available space
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM vw_team_cap_summary
                WHERE team_id = ? AND season = ? AND dynasty_id = ?
            ''', (team_id, season, dynasty_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ========================================================================
    # FRANCHISE TAG & TENDER OPERATIONS
    # ========================================================================

    def insert_franchise_tag(
        self,
        player_id: int,
        team_id: int,
        season: int,
        dynasty_id: str,
        tag_type: str,
        tag_salary: int,
        tag_date: date,
        deadline_date: date,
        consecutive_tag_number: int = 1
    ) -> int:
        """
        Insert franchise tag record.

        Args:
            player_id: Player ID
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            tag_type: FRANCHISE_EXCLUSIVE, FRANCHISE_NON_EXCLUSIVE, or TRANSITION
            tag_salary: Tag salary amount
            tag_date: Date tag was applied
            deadline_date: Deadline for signing extension
            consecutive_tag_number: 1st, 2nd, or 3rd consecutive tag

        Returns:
            tag_id of inserted record
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute('''
                INSERT INTO franchise_tags (
                    player_id, team_id, season, dynasty_id,
                    tag_type, tag_salary,
                    tag_date, deadline_date,
                    consecutive_tag_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                player_id, team_id, season, dynasty_id,
                tag_type, tag_salary,
                tag_date, deadline_date,
                consecutive_tag_number
            ))
            conn.commit()
            return cursor.lastrowid

    def insert_rfa_tender(
        self,
        player_id: int,
        team_id: int,
        season: int,
        dynasty_id: str,
        tender_level: str,
        tender_salary: int,
        tender_date: date,
        compensation_round: Optional[int] = None
    ) -> int:
        """
        Insert RFA tender record.

        Args:
            player_id: Player ID
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            tender_level: FIRST_ROUND, SECOND_ROUND, ORIGINAL_ROUND, RIGHT_OF_FIRST_REFUSAL
            tender_salary: Tender amount
            tender_date: Date tender was offered
            compensation_round: Draft round for compensation (None for ROFR only)

        Returns:
            tender_id of inserted record
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute('''
                INSERT INTO rfa_tenders (
                    player_id, team_id, season, dynasty_id,
                    tender_level, tender_salary, tender_date,
                    compensation_round
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                player_id, team_id, season, dynasty_id,
                tender_level, tender_salary, tender_date,
                compensation_round
            ))
            conn.commit()
            return cursor.lastrowid

    # ========================================================================
    # DEAD MONEY OPERATIONS
    # ========================================================================

    def insert_dead_money(
        self,
        team_id: int,
        player_id: int,
        season: int,
        dynasty_id: str,
        contract_id: int,
        release_date: date,
        dead_money_amount: int,
        current_year_dead_money: int,
        next_year_dead_money: int,
        remaining_signing_bonus: int,
        guaranteed_salary: int = 0,
        is_june_1_designation: bool = False
    ) -> int:
        """
        Insert dead money record for released player.

        Args:
            team_id: Team ID
            player_id: Player ID
            season: Season year
            dynasty_id: Dynasty identifier
            contract_id: Original contract ID
            release_date: Date player was released
            dead_money_amount: Total dead money
            current_year_dead_money: Dead money in current year
            next_year_dead_money: Dead money in next year (June 1 split)
            remaining_signing_bonus: Remaining bonus proration
            guaranteed_salary: Guaranteed salary accelerated
            is_june_1_designation: Whether June 1 designation used

        Returns:
            dead_money_id of inserted record
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute('''
                INSERT INTO dead_money (
                    team_id, player_id, season, dynasty_id,
                    contract_id, release_date,
                    dead_money_amount,
                    is_june_1_designation,
                    current_year_dead_money, next_year_dead_money,
                    remaining_signing_bonus, guaranteed_salary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                team_id, player_id, season, dynasty_id,
                contract_id, release_date,
                dead_money_amount,
                is_june_1_designation,
                current_year_dead_money, next_year_dead_money,
                remaining_signing_bonus, guaranteed_salary
            ))
            conn.commit()
            return cursor.lastrowid

    def get_team_dead_money(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all dead money entries for a team in a season.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            List of dead money dicts
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM dead_money
                WHERE team_id = ? AND season = ? AND dynasty_id = ?
                ORDER BY dead_money_amount DESC
            ''', (team_id, season, dynasty_id))
            return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # TRANSACTION LOGGING
    # ========================================================================

    def log_transaction(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        transaction_type: str,
        transaction_date: date,
        player_id: Optional[int] = None,
        contract_id: Optional[int] = None,
        cap_impact_current: int = 0,
        cap_impact_future: Optional[Dict[int, int]] = None,
        cash_impact: int = 0,
        dead_money_created: int = 0,
        description: Optional[str] = None
    ) -> int:
        """
        Log cap transaction.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            transaction_type: SIGNING, RELEASE, RESTRUCTURE, TRADE, TAG, TENDER
            transaction_date: Date of transaction
            player_id: Player ID (if applicable)
            contract_id: Contract ID (if applicable)
            cap_impact_current: Impact on current year cap
            cap_impact_future: Dict of {year: impact} for future years
            cash_impact: Cash spending impact
            dead_money_created: Dead money created
            description: Transaction description

        Returns:
            transaction_id of logged transaction
        """
        cap_impact_future_json = json.dumps(cap_impact_future) if cap_impact_future else None

        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute('''
                INSERT INTO cap_transactions (
                    team_id, season, dynasty_id,
                    transaction_type, player_id, contract_id,
                    transaction_date,
                    cap_impact_current, cap_impact_future,
                    cash_impact, dead_money_created,
                    description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                team_id, season, dynasty_id,
                transaction_type, player_id, contract_id,
                transaction_date,
                cap_impact_current, cap_impact_future_json,
                cash_impact, dead_money_created,
                description
            ))
            conn.commit()
            return cursor.lastrowid

    def get_team_transactions(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        transaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for a team.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            transaction_type: Optional filter by type

        Returns:
            List of transaction dicts
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row

            query = '''
                SELECT * FROM cap_transactions
                WHERE team_id = ? AND season = ? AND dynasty_id = ?
            '''
            params = [team_id, season, dynasty_id]

            if transaction_type:
                query += " AND transaction_type = ?"
                params.append(transaction_type)

            query += " ORDER BY transaction_date DESC, created_at DESC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            # Parse JSON cap_impact_future
            results = []
            for row in rows:
                row_dict = dict(row)
                if row_dict.get('cap_impact_future'):
                    row_dict['cap_impact_future'] = json.loads(row_dict['cap_impact_future'])
                results.append(row_dict)

            return results

    # ========================================================================
    # LEAGUE CAP HISTORY
    # ========================================================================

    def get_salary_cap_for_season(self, season: int) -> Optional[int]:
        """
        Get league-wide salary cap for a season.

        Args:
            season: Season year

        Returns:
            Salary cap amount or None if not found
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute('''
                SELECT salary_cap_amount FROM league_salary_cap_history
                WHERE season = ?
            ''', (season,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_cap_history(self, start_year: int, end_year: int) -> List[Dict[str, Any]]:
        """
        Get salary cap history across years.

        Args:
            start_year: Start year
            end_year: End year

        Returns:
            List of cap history dicts
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM league_salary_cap_history
                WHERE season BETWEEN ? AND ?
                ORDER BY season
            ''', (start_year, end_year))
            return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # FRANCHISE TAG QUERY OPERATIONS
    # ========================================================================

    def get_player_franchise_tags(
        self,
        player_id: int,
        team_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all franchise tags for a player with a specific team.

        Args:
            player_id: Player ID
            team_id: Team ID

        Returns:
            List of franchise tag records
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM franchise_tags
                WHERE player_id = ? AND team_id = ?
                ORDER BY season DESC
            ''', (player_id, team_id))
            return [dict(row) for row in cursor.fetchall()]

    def get_team_franchise_tags(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all franchise tags used by team in a season.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            List of franchise tag records
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM franchise_tags
                WHERE team_id = ? AND season = ? AND dynasty_id = ?
            ''', (team_id, season, dynasty_id))
            return [dict(row) for row in cursor.fetchall()]

    def update_franchise_tag_contract(
        self,
        tag_id: int,
        contract_id: int
    ) -> None:
        """
        Link a contract to a franchise tag.

        Args:
            tag_id: Franchise tag ID
            contract_id: Contract ID
        """
        with sqlite3.connect(self.database_path) as conn:
            conn.execute('''
                UPDATE franchise_tags
                SET extension_contract_id = ?
                WHERE tag_id = ?
            ''', (contract_id, tag_id))
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.

        Returns:
            SQLite connection

        Note: Caller is responsible for closing connection.
        """
        conn = sqlite3.connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
