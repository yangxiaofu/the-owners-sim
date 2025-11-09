"""
Contract Transition Service

Handles contract year increments and expiration detection during offseason-to-preseason transitions.
Part of Milestone 1: Complete Multi-Year Season Cycle implementation.

This service manages the lifecycle of player contracts across season transitions,
ensuring contracts expire properly and maintaining data integrity for multi-year dynasties.
"""

import logging
import sqlite3
from typing import List, Dict, Any, Optional

from src.constants.team_ids import TeamIDs


class ContractTransitionService:
    """
    Service for managing contract year increments and expirations.

    Responsibilities:
    - Increment contract years for all active contracts
    - Detect expiring contracts
    - Deactivate expired contracts
    - Log detailed contract expiration audit trail

    Follows service extraction pattern from Phase 3 (TransactionService).
    Uses dependency injection for testability.

    Note: We do NOT increment current_year on contracts because contract_year_details
    uses absolute season_year (2025, 2026) not relative years (1, 2, 3). The season_year
    parameter acts as the "current year" cursor for determining which contracts have expired.
    """

    def __init__(self, cap_api, dynasty_id: str):
        """
        Initialize contract transition service.

        Args:
            cap_api: CapDatabaseAPI instance for contract operations
            dynasty_id: Dynasty context for isolation
        """
        self.cap_api = cap_api
        self.dynasty_id = dynasty_id
        self.logger = logging.getLogger(self.__class__.__name__)

    def increment_all_contracts(self, season_year: int) -> Dict[str, Any]:
        """
        Increment contract years for all active contracts in dynasty.

        Logic:
        - Query all active contracts (is_active=True)
        - For each contract, check if end_year < season_year:
          - If yes: Mark as expired (call deactivate_expired_contracts)
          - If no: Continue (contract still active)

        NOTE: We do NOT increment current_year because contract_year_details
        uses absolute season_year (2025, 2026) not relative years (1, 2, 3).

        Args:
            season_year: New season year (e.g., 2025)

        Returns:
            Dict with:
                - total_contracts: Total active contracts processed
                - still_active: Contracts still valid after check
                - expired_count: Contracts that expired
        """
        self.logger.info(
            f"[CONTRACT_TRANSITION] Starting contract increment for season {season_year} "
            f"(dynasty: {self.dynasty_id})"
        )

        try:
            # Get all active contracts across all teams
            total_active_contracts = 0
            all_contracts = []

            for team_id in range(1, 33):  # All 32 NFL teams
                team_contracts = self.cap_api.get_team_contracts(
                    team_id=team_id,
                    season=season_year - 1,  # Query previous season to get all contracts
                    dynasty_id=self.dynasty_id,
                    active_only=True
                )
                total_active_contracts += len(team_contracts)
                all_contracts.extend(team_contracts)

            self.logger.info(
                f"[CONTRACT_TRANSITION] Found {total_active_contracts} active contracts "
                f"to evaluate for season {season_year}"
            )

            # Deactivate expired contracts (end_year < season_year)
            expired_count = self.deactivate_expired_contracts(season_year)

            # Calculate still active contracts
            still_active = total_active_contracts - expired_count

            self.logger.info(
                f"[CONTRACT_TRANSITION] Contract increment complete | "
                f"Total: {total_active_contracts} | Still Active: {still_active} | "
                f"Expired: {expired_count}"
            )

            return {
                'total_contracts': total_active_contracts,
                'still_active': still_active,
                'expired_count': expired_count
            }

        except Exception as e:
            self.logger.error(f"[CONTRACT_TRANSITION] Error during contract increment: {e}")
            raise

    def get_expiring_contracts(self, season_year: int) -> List[Dict[str, Any]]:
        """
        Get all contracts expiring at end of this season.

        Uses CapDatabaseAPI.get_expiring_contracts() method.
        Queries contracts WHERE end_year = season_year AND is_active = TRUE.

        Args:
            season_year: Season year to check (e.g., 2024)

        Returns:
            List of contract dicts with player_id, team_id, end_year, etc.
        """
        self.logger.info(
            f"[CONTRACT_TRANSITION] Querying expiring contracts for season {season_year} "
            f"(dynasty: {self.dynasty_id})"
        )

        try:
            all_expiring = []

            # Query each team for expiring contracts
            for team_id in range(1, 33):  # All 32 NFL teams
                team_expiring = self.cap_api.get_expiring_contracts(
                    team_id=team_id,
                    season=season_year,
                    dynasty_id=self.dynasty_id,
                    active_only=True
                )
                all_expiring.extend(team_expiring)

            self.logger.info(
                f"[CONTRACT_TRANSITION] Found {len(all_expiring)} contracts expiring "
                f"at end of season {season_year}"
            )

            return all_expiring

        except Exception as e:
            self.logger.error(
                f"[CONTRACT_TRANSITION] Error querying expiring contracts: {e}"
            )
            raise

    def deactivate_expired_contracts(self, season_year: int) -> int:
        """
        Mark all expired contracts as inactive.

        Logic:
        - Query contracts WHERE end_year < season_year AND is_active = TRUE
        - UPDATE player_contracts SET is_active = FALSE WHERE contract_id IN (...)

        Args:
            season_year: Current season year (e.g., 2025)

        Returns:
            Count of contracts deactivated
        """
        self.logger.info(
            f"[CONTRACT_TRANSITION] Deactivating expired contracts (end_year < {season_year}, "
            f"dynasty: {self.dynasty_id})"
        )

        try:
            # Get database connection
            conn = self.cap_api._get_connection()

            try:
                # Query expired contracts before deactivating (for logging)
                cursor = conn.execute('''
                    SELECT contract_id, player_id, team_id, end_year, contract_years, total_value
                    FROM player_contracts
                    WHERE end_year < ?
                      AND dynasty_id = ?
                      AND is_active = TRUE
                ''', (season_year, self.dynasty_id))

                expired_contracts = [dict(zip([col[0] for col in cursor.description], row))
                                   for row in cursor.fetchall()]

                # Log expiring contracts for audit trail
                if expired_contracts:
                    self.log_contract_expirations(expired_contracts)

                # Deactivate expired contracts
                cursor = conn.execute('''
                    UPDATE player_contracts
                    SET is_active = FALSE,
                        modified_at = CURRENT_TIMESTAMP
                    WHERE end_year < ?
                      AND dynasty_id = ?
                      AND is_active = TRUE
                ''', (season_year, self.dynasty_id))

                conn.commit()
                expired_count = cursor.rowcount

                self.logger.info(
                    f"[CONTRACT_TRANSITION] Deactivated {expired_count} expired contracts "
                    f"(end_year < {season_year})"
                )

                return expired_count

            finally:
                conn.close()

        except Exception as e:
            self.logger.error(
                f"[CONTRACT_TRANSITION] Error deactivating expired contracts: {e}"
            )
            raise

    def log_contract_expirations(self, expired_contracts: List[Dict[str, Any]]) -> None:
        """
        Log detailed audit trail of contract expirations (per user requirement).

        Format:
        "CONTRACT EXPIRATION REPORT - Season 2025"
        "  Player ID 12345 (Team 1, QB) - 4-year contract expired"
        "  Player ID 67890 (Team 15, WR) - 3-year contract expired"
        "Total: 47 contracts expired, 47 new free agents"

        Args:
            expired_contracts: List of expired contract dicts
        """
        if not expired_contracts:
            self.logger.info("[CONTRACT_EXPIRATION_REPORT] No contracts expired this season")
            return

        # Extract season year from first contract
        season_year = expired_contracts[0].get('end_year', 'UNKNOWN')

        self.logger.info(f"CONTRACT EXPIRATION REPORT - Season {season_year}")
        self.logger.info("=" * 80)

        for contract in expired_contracts:
            player_id = contract.get('player_id', 'UNKNOWN')
            team_id = contract.get('team_id', 'UNKNOWN')
            contract_years = contract.get('contract_years', 'UNKNOWN')
            total_value = contract.get('total_value', 0)

            # Format total value with commas
            value_str = f"${total_value:,}" if isinstance(total_value, (int, float)) else str(total_value)

            self.logger.info(
                f"  Player ID {player_id} (Team {team_id}) - "
                f"{contract_years}-year contract expired ({value_str})"
            )

        self.logger.info("=" * 80)
        self.logger.info(
            f"Total: {len(expired_contracts)} contracts expired, "
            f"{len(expired_contracts)} new free agents"
        )
        self.logger.info("")
