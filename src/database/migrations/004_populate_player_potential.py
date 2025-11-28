"""
Migration: Populate player potential in attributes JSON

Adds 'potential' field to existing players' attributes JSON blob.
Part of Tollgate 3: Individual Player Potential implementation.

Potential represents the maximum achievable overall rating for a player.
Formula:
- Young players (age < 27): overall + random(3, 8)
- Prime/veteran players (age >= 27): overall + random(0, 3)
- Capped at 99
"""

import sqlite3
import json
import random
from pathlib import Path


class PlayerPotentialMigration:
    """Migration to add potential to existing player attributes."""

    # Database paths for both systems
    GAME_CYCLE_DB = "data/database/game_cycle/game_cycle.db"
    LEGACY_DB = "data/database/nfl_simulation.db"

    def __init__(self, db_path: str = None):
        """
        Initialize migration.

        Args:
            db_path: Path to database. If None, uses game cycle DB.
        """
        self.db_path = db_path or self.GAME_CYCLE_DB

    def up(self, dynasty_id: str = None, current_season: int = 2025) -> int:
        """
        Apply migration: add potential to player attributes.

        Args:
            dynasty_id: Optional dynasty_id to limit migration scope.
                       If None, migrates all players.
            current_season: Current season year for age calculation.

        Returns:
            Number of players updated.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        updated = 0

        try:
            # Get all players (optionally filtered by dynasty)
            if dynasty_id:
                cursor.execute("""
                    SELECT player_id, attributes, birthdate, dynasty_id
                    FROM players
                    WHERE dynasty_id = ?
                """, (dynasty_id,))
            else:
                cursor.execute("""
                    SELECT player_id, attributes, birthdate, dynasty_id
                    FROM players
                """)

            rows = cursor.fetchall()
            print(f"Processing {len(rows)} players...")

            for row in rows:
                player_id = row['player_id']
                attrs_json = row['attributes']
                birthdate = row['birthdate']
                player_dynasty = row['dynasty_id']

                # Parse attributes
                if isinstance(attrs_json, str):
                    attrs = json.loads(attrs_json)
                else:
                    attrs = attrs_json or {}

                # Skip if already has potential
                if 'potential' in attrs:
                    continue

                # Calculate age from birthdate
                age = self._calculate_age(birthdate, current_season)

                # Get current overall
                overall = int(attrs.get('overall', 70))

                # Calculate potential based on age
                potential = self._calculate_potential(overall, age)
                attrs['potential'] = potential

                # Update in database
                cursor.execute("""
                    UPDATE players
                    SET attributes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE dynasty_id = ? AND player_id = ?
                """, (json.dumps(attrs), player_dynasty, player_id))
                updated += 1

            conn.commit()
            print(f"✅ Migration completed: {updated} players updated with potential")
            return updated

        except Exception as e:
            conn.rollback()
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            conn.close()

    def _calculate_age(self, birthdate: str, current_season: int) -> int:
        """Calculate age from birthdate string (YYYY-MM-DD)."""
        if not birthdate:
            return 25  # Default age
        try:
            birth_year = int(birthdate.split("-")[0])
            return current_season - birth_year
        except (ValueError, IndexError):
            return 25

    def _calculate_potential(self, overall: int, age: int) -> int:
        """
        Calculate potential for an existing player.

        Args:
            overall: Current overall rating
            age: Player's age

        Returns:
            Potential rating (capped at 99)
        """
        if age < 27:
            # Young players have more growth potential
            bonus = random.randint(3, 8)
        else:
            # Prime/veteran players have less growth room
            bonus = random.randint(0, 3)

        return min(99, overall + bonus)

    def down(self) -> int:
        """
        Rollback migration: remove potential from player attributes.

        Returns:
            Number of players updated.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        updated = 0

        try:
            cursor.execute("SELECT player_id, attributes, dynasty_id FROM players")
            rows = cursor.fetchall()

            for row in rows:
                player_id = row['player_id']
                attrs_json = row['attributes']
                dynasty_id = row['dynasty_id']

                if isinstance(attrs_json, str):
                    attrs = json.loads(attrs_json)
                else:
                    attrs = attrs_json or {}

                if 'potential' in attrs:
                    del attrs['potential']
                    cursor.execute("""
                        UPDATE players
                        SET attributes = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE dynasty_id = ? AND player_id = ?
                    """, (json.dumps(attrs), dynasty_id, player_id))
                    updated += 1

            conn.commit()
            print(f"✅ Rollback completed: {updated} players had potential removed")
            return updated

        except Exception as e:
            conn.rollback()
            print(f"❌ Rollback failed: {e}")
            raise
        finally:
            conn.close()

    def check_status(self) -> dict:
        """
        Check migration status.

        Returns:
            Dict with counts of players with/without potential.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM players")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT attributes FROM players")
            rows = cursor.fetchall()

            with_potential = 0
            without_potential = 0

            for row in rows:
                attrs = json.loads(row[0]) if row[0] else {}
                if 'potential' in attrs:
                    with_potential += 1
                else:
                    without_potential += 1

            return {
                "total_players": total,
                "with_potential": with_potential,
                "without_potential": without_potential,
                "migration_complete": without_potential == 0
            }

        finally:
            conn.close()


def populate_existing_player_potential(
    db_path: str,
    dynasty_id: str = None,
    current_season: int = 2025
) -> int:
    """
    Convenience function to run the migration.

    This is the main entry point for populating potential on existing players.

    Args:
        db_path: Path to database
        dynasty_id: Optional dynasty to limit scope
        current_season: Current season for age calculation

    Returns:
        Number of players updated
    """
    migration = PlayerPotentialMigration(db_path)
    return migration.up(dynasty_id=dynasty_id, current_season=current_season)


if __name__ == '__main__':
    import sys

    # Determine which database to use
    db_path = PlayerPotentialMigration.GAME_CYCLE_DB
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    print(f"Running migration on: {db_path}")

    migration = PlayerPotentialMigration(db_path)

    # Check status first
    status = migration.check_status()
    print(f"Before migration: {status}")

    if status['without_potential'] > 0:
        # Run migration
        updated = migration.up()
        print(f"Updated {updated} players")

        # Verify
        status_after = migration.check_status()
        print(f"After migration: {status_after}")
    else:
        print("All players already have potential. Skipping migration.")
