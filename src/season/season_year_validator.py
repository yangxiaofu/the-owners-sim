"""
Season Year Validator

Validates synchronization between controller's season_year and database's dynasty_state.season.

Part of Single Source of Truth implementation (Phase 1: Observation & Validation).
This module detects drift without changing behavior, providing visibility into the problem.
"""

from typing import Optional, Tuple
import logging


class SeasonYearValidator:
    """
    Validates that in-memory season_year matches database source of truth.

    This is a diagnostic tool that detects desynchronization between:
    - Controller's self.season_year (in-memory)
    - dynasty_state.season (database - source of truth)

    When drift is detected, the validator can:
    1. Log warnings (Phase 1 - current)
    2. Trigger auto-recovery (Phase 5 - future)

    Usage:
        validator = SeasonYearValidator()
        is_synced, db_year = validator.validate_sync(
            controller_year=self.season_year,
            dynasty_id=self.dynasty_id,
            dynasty_api=self.dynasty_api
        )

        if not is_synced:
            logger.warning(f"Desync detected: controller={controller_year}, database={db_year}")
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize validator.

        Args:
            logger: Optional logger for warnings. If None, creates default logger.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def validate_sync(
        self,
        controller_year: int,
        dynasty_id: str,
        dynasty_api
    ) -> Tuple[bool, int]:
        """
        Check if controller's year matches database.

        This method queries the database to find the authoritative season year
        and compares it with the controller's in-memory copy.

        Args:
            controller_year: Season year from controller (in-memory)
            dynasty_id: Dynasty identifier
            dynasty_api: DynastyStateAPI instance for database queries

        Returns:
            Tuple of (is_synchronized, database_year):
            - is_synchronized: True if controller matches database
            - database_year: The authoritative year from database

        Examples:
            >>> validator.validate_sync(2025, "test_dynasty", dynasty_api)
            (True, 2025)  # Synchronized

            >>> validator.validate_sync(2027, "test_dynasty", dynasty_api)
            (False, 2025)  # Desynchronized - controller ahead by 2 years
        """
        # First try: Query with controller's year
        db_state = dynasty_api.get_current_state(dynasty_id, controller_year)

        if db_state:
            # Found state with controller's year
            db_year = db_state.get('season', controller_year)
            is_synced = (controller_year == db_year)

            if not is_synced:
                self.logger.warning(
                    f"[YEAR_DRIFT] Controller year ({controller_year}) != "
                    f"Database year ({db_year}) for dynasty '{dynasty_id}'"
                )

            return (is_synced, db_year)

        # State not found with controller's year
        # Try nearby years (±3 range) to find actual database value
        self.logger.info(
            f"[YEAR_QUERY] No state found for dynasty '{dynasty_id}' with season={controller_year}. "
            f"Searching nearby years..."
        )

        for offset in range(1, 4):  # Check ±1, ±2, ±3
            # Try lower years first (more likely during drift)
            for year in [controller_year - offset, controller_year + offset]:
                db_state = dynasty_api.get_current_state(dynasty_id, year)
                if db_state:
                    db_year = db_state.get('season', year)
                    self.logger.warning(
                        f"[YEAR_DRIFT] Found database state at season={db_year}, "
                        f"but controller has season={controller_year}. "
                        f"Drift of {abs(controller_year - db_year)} year(s) detected!"
                    )
                    return (False, db_year)

        # No state found in ±3 range
        # This could be a new dynasty or corrupted database
        self.logger.error(
            f"[YEAR_MISSING] No dynasty_state found for dynasty '{dynasty_id}' "
            f"in range [{controller_year - 3}, {controller_year + 3}]. "
            f"Assuming controller year is correct: {controller_year}"
        )

        # Return controller's year as fallback (may be wrong, but no better option)
        return (True, controller_year)  # Technically not "synced" but no database to sync to

    def validate_with_recovery(
        self,
        controller_year: int,
        dynasty_id: str,
        dynasty_api
    ) -> Tuple[bool, int, bool]:
        """
        Validate sync and determine if auto-recovery is possible.

        Extended version of validate_sync() that also returns whether
        the drift can be auto-corrected (i.e., database state exists).

        Args:
            controller_year: Season year from controller
            dynasty_id: Dynasty identifier
            dynasty_api: DynastyStateAPI instance

        Returns:
            Tuple of (is_synchronized, database_year, can_recover):
            - is_synchronized: True if controller matches database
            - database_year: The authoritative year from database
            - can_recover: True if database state found (can auto-correct)

        Examples:
            >>> validator.validate_with_recovery(2027, "test", api)
            (False, 2025, True)  # Can recover - sync to 2025

            >>> validator.validate_with_recovery(2025, "new", api)
            (True, 2025, False)  # No database state - new dynasty
        """
        is_synced, db_year = self.validate_sync(controller_year, dynasty_id, dynasty_api)

        # Can recover if we found database state (even if year differs)
        if not is_synced and db_year != controller_year:
            # Found different year in database - can recover
            can_recover = True
        else:
            # Either synced or no database state found
            can_recover = False

        return (is_synced, db_year, can_recover)

    def log_validation_report(
        self,
        controller_year: int,
        dynasty_id: str,
        dynasty_api,
        context: str = ""
    ) -> bool:
        """
        Validate and log detailed report.

        Convenience method that performs validation and logs a detailed
        report of the results. Useful for debugging and monitoring.

        Args:
            controller_year: Season year from controller
            dynasty_id: Dynasty identifier
            dynasty_api: DynastyStateAPI instance
            context: Optional context string (e.g., "Before phase transition")

        Returns:
            True if synchronized, False if drift detected
        """
        is_synced, db_year, can_recover = self.validate_with_recovery(
            controller_year, dynasty_id, dynasty_api
        )

        prefix = f"[{context}] " if context else ""

        if is_synced:
            self.logger.debug(
                f"{prefix}✓ Season year synchronized: "
                f"controller={controller_year}, database={db_year}"
            )
        else:
            drift = abs(controller_year - db_year)
            direction = "ahead" if controller_year > db_year else "behind"

            self.logger.warning(
                f"{prefix}✗ Season year DRIFT detected:\n"
                f"  Controller: {controller_year}\n"
                f"  Database:   {db_year}\n"
                f"  Drift:      {drift} year(s) {direction}\n"
                f"  Dynasty:    {dynasty_id}\n"
                f"  Recovery:   {'Possible' if can_recover else 'NOT POSSIBLE'}"
            )

        return is_synced
