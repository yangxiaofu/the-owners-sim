"""
Retention Policy Manager for Statistics Preservation System

Manages retention policies for historical data. Determines which seasons
should be kept in hot storage (full detail) vs archived (summaries only).

Key Features:
- Per-dynasty configuration
- Multiple policy types (keep_all, keep_n_seasons, summary_only)
- Clear business logic separation
- No database writes (read-only policy evaluation)
"""

from typing import List, Optional
import logging
import sqlite3

from statistics.models import RetentionPolicy


class RetentionPolicyManager:
    """
    Manage retention policies for historical data.

    Determines which seasons should be kept in hot storage vs archived.
    Supports per-dynasty configuration with three policy types:

    - keep_all: Never archive (keep full detail forever)
    - keep_n_seasons: Keep last N seasons in full detail
    - summary_only: Archive all seasons immediately

    Design Philosophy:
    - Pure business logic (no side effects)
    - Read-only operations for policy evaluation
    - Clear, testable decision-making
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        database_conn: Optional[sqlite3.Connection] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize retention policy manager.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for isolation
            database_conn: Optional external database connection
            logger: Optional logger instance
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.external_conn = database_conn
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Cache policy to avoid repeated database queries
        self._cached_policy: Optional[RetentionPolicy] = None

    def get_retention_policy(self) -> RetentionPolicy:
        """
        Get retention policy for this dynasty.

        Returns cached policy if available, otherwise loads from database.
        Creates default policy if none exists.

        Returns:
            RetentionPolicy dataclass with:
            - policy_type: 'keep_all' | 'keep_n_seasons' | 'summary_only'
            - retention_seasons: Number of seasons to keep
            - auto_archive: Whether to automatically archive

        Raises:
            sqlite3.Error: If database query fails
        """
        # Return cached policy if available
        if self._cached_policy:
            return self._cached_policy

        conn = self._get_connection()

        try:
            query = """
            SELECT
                dynasty_id,
                policy_type,
                retention_seasons,
                auto_archive,
                last_archival_season,
                last_archival_timestamp,
                total_seasons_archived,
                created_at,
                updated_at
            FROM archival_config
            WHERE dynasty_id = ?
            """

            cursor = conn.cursor()
            cursor.execute(query, (self.dynasty_id,))
            row = cursor.fetchone()

            if row:
                policy = RetentionPolicy(
                    dynasty_id=row['dynasty_id'],
                    policy_type=row['policy_type'],
                    retention_seasons=row['retention_seasons'],
                    auto_archive=bool(row['auto_archive']),
                    last_archival_season=row['last_archival_season'],
                    last_archival_timestamp=row['last_archival_timestamp'],
                    total_seasons_archived=row['total_seasons_archived']
                )
            else:
                # Create default policy if none exists
                policy = self._create_default_policy()

            # Cache the policy
            self._cached_policy = policy

            return policy

        except sqlite3.Error as e:
            self.logger.error(
                f"Error loading retention policy for dynasty '{self.dynasty_id}': {e}",
                exc_info=True
            )
            raise

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

    def should_archive_season(
        self,
        season: int,
        current_season: int
    ) -> bool:
        """
        Determine if a season should be archived.

        Business rules:
        - keep_all: Never archive
        - keep_n_seasons: Archive if older than N seasons from current
        - summary_only: Always archive

        Args:
            season: Season year to check
            current_season: Current season year

        Returns:
            True if season exceeds retention window and should be archived

        Examples:
            >>> manager = RetentionPolicyManager(db_path, "my_dynasty")
            >>> # Policy: keep_n_seasons with retention_seasons=3
            >>> # Current season: 2030
            >>> manager.should_archive_season(2026, 2030)  # 4 years old
            True
            >>> manager.should_archive_season(2028, 2030)  # 2 years old
            False
        """
        policy = self.get_retention_policy()

        # keep_all: Never archive
        if policy.policy_type == "keep_all":
            return False

        # summary_only: Always archive
        if policy.policy_type == "summary_only":
            return True

        # keep_n_seasons: Archive if beyond retention window
        if policy.policy_type == "keep_n_seasons":
            seasons_old = current_season - season

            # Keep current season and last N-1 completed seasons
            # Example: retention_seasons=3, current=2030
            # Keep: 2030 (current), 2029, 2028
            # Archive: 2027 and earlier
            return seasons_old >= policy.retention_seasons

        # Unknown policy type (should never happen due to DB constraint)
        self.logger.warning(
            f"Unknown policy type '{policy.policy_type}', defaulting to keep_all"
        )
        return False

    def get_seasons_to_archive(
        self,
        current_season: int,
        all_seasons: Optional[List[int]] = None
    ) -> List[int]:
        """
        Get list of seasons that should be archived.

        Args:
            current_season: Current season year
            all_seasons: Optional list of all season years (if not provided,
                        queries database for all completed seasons)

        Returns:
            List of season years that should be archived

        Examples:
            >>> manager = RetentionPolicyManager(db_path, "my_dynasty")
            >>> # Policy: keep_n_seasons with retention_seasons=3
            >>> # Current season: 2030
            >>> manager.get_seasons_to_archive(2030, [2025, 2026, 2027, 2028, 2029])
            [2025, 2026]  # 2027, 2028, 2029 are kept (last 3 seasons)
        """
        # Get all seasons if not provided
        if all_seasons is None:
            all_seasons = self._get_all_completed_seasons()

        # Filter seasons that should be archived
        seasons_to_archive = [
            season for season in all_seasons
            if self.should_archive_season(season, current_season)
        ]

        return sorted(seasons_to_archive)

    def update_policy(
        self,
        retention_seasons: Optional[int] = None,
        policy_type: Optional[str] = None,
        auto_archive: Optional[bool] = None
    ) -> None:
        """
        Update retention policy in database.

        This method writes to the database, unlike other methods which
        are read-only. Should only be called by StatisticsArchiver or
        configuration UI.

        Args:
            retention_seasons: Optional new retention period
            policy_type: Optional new policy type
            auto_archive: Optional auto-archive flag

        Raises:
            ValueError: If retention_seasons is invalid
            sqlite3.Error: If database update fails
        """
        # Validate retention_seasons
        if retention_seasons is not None:
            if retention_seasons < 0 or retention_seasons > 100:
                raise ValueError(
                    f"retention_seasons must be 0-100, got {retention_seasons}"
                )

        # Validate policy_type
        if policy_type is not None:
            valid_types = ["keep_all", "keep_n_seasons", "summary_only"]
            if policy_type not in valid_types:
                raise ValueError(
                    f"policy_type must be one of {valid_types}, got '{policy_type}'"
                )

        conn = self._get_connection()

        try:
            # Build update query dynamically
            updates = []
            params = []

            if retention_seasons is not None:
                updates.append("retention_seasons = ?")
                params.append(retention_seasons)

            if policy_type is not None:
                updates.append("policy_type = ?")
                params.append(policy_type)

            if auto_archive is not None:
                updates.append("auto_archive = ?")
                params.append(auto_archive)

            if not updates:
                self.logger.warning("update_policy called with no updates")
                return

            # Always update updated_at timestamp
            updates.append("updated_at = CURRENT_TIMESTAMP")

            query = f"""
            UPDATE archival_config
            SET {", ".join(updates)}
            WHERE dynasty_id = ?
            """
            params.append(self.dynasty_id)

            cursor = conn.cursor()
            cursor.execute(query, params)

            # Commit if we created the connection
            if not self.external_conn:
                conn.commit()

            # Invalidate cache
            self._cached_policy = None

            self.logger.info(
                f"Updated retention policy for dynasty '{self.dynasty_id}': "
                f"retention_seasons={retention_seasons}, policy_type={policy_type}, "
                f"auto_archive={auto_archive}"
            )

        except sqlite3.Error as e:
            self.logger.error(
                f"Error updating retention policy for dynasty '{self.dynasty_id}': {e}",
                exc_info=True
            )
            raise

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

    def _create_default_policy(self) -> RetentionPolicy:
        """
        Create default retention policy.

        Default: keep_n_seasons with retention_seasons=3

        Returns:
            Default RetentionPolicy dataclass
        """
        return RetentionPolicy(
            dynasty_id=self.dynasty_id,
            policy_type="keep_n_seasons",
            retention_seasons=3,
            auto_archive=True,
            total_seasons_archived=0
        )

    def _get_all_completed_seasons(self) -> List[int]:
        """
        Get all completed seasons for this dynasty from database.

        Returns:
            List of season years (sorted ascending)
        """
        conn = self._get_connection()

        try:
            query = """
            SELECT DISTINCT season
            FROM games
            WHERE dynasty_id = ?
            ORDER BY season ASC
            """

            cursor = conn.cursor()
            cursor.execute(query, (self.dynasty_id,))
            rows = cursor.fetchall()

            return [row['season'] for row in rows]

        except sqlite3.Error as e:
            self.logger.error(
                f"Error fetching completed seasons for dynasty '{self.dynasty_id}': {e}"
            )
            return []

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection (either external or create new).

        Returns:
            SQLite connection with row_factory set
        """
        if self.external_conn:
            return self.external_conn

        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn
