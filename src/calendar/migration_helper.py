"""
Migration Helper

Utility for migrating calendar data between different storage systems.
Helps transition from in-memory EventStore to database-backed EventManager.
"""

import json
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .event import Event
from .event_store import EventStore
from .event_manager import EventManager


class CalendarMigrationHelper:
    """
    Helper class for migrating calendar data between storage systems.

    Provides utilities for backup, restore, and migration of calendar events
    from legacy in-memory storage to database-backed storage.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize the migration helper.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.logger = logging.getLogger("CalendarMigrationHelper")

    def export_events_to_json(self, event_store: EventStore,
                             output_file: str) -> Tuple[bool, Optional[str]]:
        """
        Export events from EventStore to JSON file.

        Args:
            event_store: EventStore instance to export from
            output_file: Path to output JSON file

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Get all events from the store
            all_events = event_store.get_all_events()

            # Convert events to serializable format
            events_data = []
            for event in all_events:
                event_data = {
                    "event_id": event.event_id,
                    "name": event.name,
                    "event_date": event.event_date.isoformat(),
                    "metadata": event.metadata
                }
                events_data.append(event_data)

            # Create export data structure
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_events": len(events_data),
                "events": events_data
            }

            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Exported {len(events_data)} events to {output_file}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to export events to JSON: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def import_events_from_json(self, event_manager: EventManager,
                               input_file: str) -> Tuple[bool, Optional[str], int]:
        """
        Import events from JSON file to EventManager.

        Args:
            event_manager: EventManager instance to import to
            input_file: Path to input JSON file

        Returns:
            Tuple[bool, Optional[str], int]: (success, error_message, imported_count)
        """
        try:
            # Read JSON file
            with open(input_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # Validate JSON structure
            if "events" not in import_data:
                return False, "Invalid JSON format: missing 'events' key", 0

            events_data = import_data["events"]
            imported_count = 0
            failed_imports = []

            # Import each event
            for event_data in events_data:
                try:
                    # Parse event data
                    event_date = datetime.fromisoformat(event_data["event_date"]).date()

                    # Create Event object
                    event = Event(
                        name=event_data["name"],
                        event_date=event_date,
                        event_id=event_data["event_id"],
                        metadata=event_data.get("metadata", {})
                    )

                    # Save to EventManager
                    success, error_msg = event_manager.save_event(event)
                    if success:
                        imported_count += 1
                    else:
                        failed_imports.append(f"{event.event_id}: {error_msg}")

                except Exception as e:
                    failed_imports.append(f"Event parse error: {str(e)}")

            # Log results
            if failed_imports:
                self.logger.warning(f"Import completed with {len(failed_imports)} failures")
                for failure in failed_imports[:5]:  # Log first 5 failures
                    self.logger.warning(f"Import failure: {failure}")

            self.logger.info(f"Successfully imported {imported_count} events from {input_file}")
            return True, None, imported_count

        except Exception as e:
            error_msg = f"Failed to import events from JSON: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, 0

    def migrate_eventstore_to_database(self, event_store: EventStore,
                                     backup_file: Optional[str] = None) -> Tuple[bool, Optional[str], int]:
        """
        Migrate events from EventStore to database-backed EventManager.

        Args:
            event_store: Source EventStore to migrate from
            backup_file: Optional backup file path before migration

        Returns:
            Tuple[bool, Optional[str], int]: (success, error_message, migrated_count)
        """
        try:
            # Create EventManager for target
            event_manager = EventManager(self.database_path)

            # Create backup if requested
            if backup_file:
                backup_success, backup_error = self.export_events_to_json(event_store, backup_file)
                if not backup_success:
                    return False, f"Backup failed: {backup_error}", 0
                self.logger.info(f"Backup created at {backup_file}")

            # Get all events from EventStore
            all_events = event_store.get_all_events()
            migrated_count = 0
            failed_migrations = []

            # Migrate each event
            for event in all_events:
                success, error_msg = event_manager.save_event(event)
                if success:
                    migrated_count += 1
                else:
                    failed_migrations.append(f"{event.event_id}: {error_msg}")

            # Log results
            if failed_migrations:
                self.logger.warning(f"Migration completed with {len(failed_migrations)} failures")
                for failure in failed_migrations[:5]:  # Log first 5 failures
                    self.logger.warning(f"Migration failure: {failure}")

            self.logger.info(f"Successfully migrated {migrated_count} events to database")
            return True, None, migrated_count

        except Exception as e:
            error_msg = f"Failed to migrate EventStore to database: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, 0

    def backup_database_events(self, output_file: str) -> Tuple[bool, Optional[str], int]:
        """
        Create a backup of all events in the database.

        Args:
            output_file: Path to backup file

        Returns:
            Tuple[bool, Optional[str], int]: (success, error_message, backed_up_count)
        """
        try:
            # Create temporary EventManager to access database
            event_manager = EventManager(self.database_path)

            # Get all events
            all_dates = event_manager.get_dates_with_events()
            all_events = []

            for event_date in all_dates:
                date_events = event_manager.get_events_by_date(event_date)
                all_events.extend(date_events)

            # Create backup data structure
            backup_data = {
                "backup_timestamp": datetime.now().isoformat(),
                "database_path": self.database_path,
                "total_events": len(all_events),
                "events": []
            }

            # Serialize events
            for event in all_events:
                event_data = {
                    "event_id": event.event_id,
                    "name": event.name,
                    "event_date": event.event_date.isoformat(),
                    "metadata": event.metadata
                }
                backup_data["events"].append(event_data)

            # Write backup file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Backed up {len(all_events)} events to {output_file}")
            return True, None, len(all_events)

        except Exception as e:
            error_msg = f"Failed to backup database events: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, 0

    def restore_database_from_backup(self, backup_file: str,
                                   clear_existing: bool = False) -> Tuple[bool, Optional[str], int]:
        """
        Restore events from backup file to database.

        Args:
            backup_file: Path to backup file
            clear_existing: Whether to clear existing events first

        Returns:
            Tuple[bool, Optional[str], int]: (success, error_message, restored_count)
        """
        try:
            # Create EventManager
            event_manager = EventManager(self.database_path)

            # Clear existing events if requested
            if clear_existing:
                cleared_count = event_manager.clear_all_events()
                self.logger.info(f"Cleared {cleared_count} existing events")

            # Import events from backup
            success, error_msg, restored_count = self.import_events_from_json(
                event_manager, backup_file
            )

            if success:
                self.logger.info(f"Successfully restored {restored_count} events from backup")
            else:
                self.logger.error(f"Failed to restore from backup: {error_msg}")

            return success, error_msg, restored_count

        except Exception as e:
            error_msg = f"Failed to restore from backup: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, 0

    def validate_migration(self, event_store: EventStore) -> Dict[str, Any]:
        """
        Validate that migration was successful by comparing EventStore to database.

        Args:
            event_store: Original EventStore to compare against

        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            # Get events from EventStore
            store_events = event_store.get_all_events()
            store_events_by_id = {event.event_id: event for event in store_events}

            # Get events from database
            event_manager = EventManager(self.database_path)
            db_dates = event_manager.get_dates_with_events()
            db_events = []

            for event_date in db_dates:
                date_events = event_manager.get_events_by_date(event_date)
                db_events.extend(date_events)

            db_events_by_id = {event.event_id: event for event in db_events}

            # Compare counts
            store_count = len(store_events)
            db_count = len(db_events)

            # Find differences
            missing_in_db = set(store_events_by_id.keys()) - set(db_events_by_id.keys())
            extra_in_db = set(db_events_by_id.keys()) - set(store_events_by_id.keys())

            # Check data consistency for common events
            data_mismatches = []
            common_ids = set(store_events_by_id.keys()) & set(db_events_by_id.keys())

            for event_id in common_ids:
                store_event = store_events_by_id[event_id]
                db_event = db_events_by_id[event_id]

                if (store_event.name != db_event.name or
                    store_event.event_date != db_event.event_date or
                    store_event.metadata != db_event.metadata):
                    data_mismatches.append(event_id)

            # Compile results
            is_successful = (store_count == db_count and
                           len(missing_in_db) == 0 and
                           len(extra_in_db) == 0 and
                           len(data_mismatches) == 0)

            validation_results = {
                "migration_successful": is_successful,
                "store_event_count": store_count,
                "database_event_count": db_count,
                "missing_in_database": list(missing_in_db),
                "extra_in_database": list(extra_in_db),
                "data_mismatches": data_mismatches,
                "validation_timestamp": datetime.now().isoformat()
            }

            self.logger.info(f"Migration validation: {'SUCCESS' if is_successful else 'FAILED'}")
            return validation_results

        except Exception as e:
            self.logger.error(f"Migration validation failed: {e}")
            return {
                "migration_successful": False,
                "error": str(e),
                "validation_timestamp": datetime.now().isoformat()
            }

    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get the current status of calendar data storage.

        Returns:
            Dict[str, Any]: Status information
        """
        try:
            event_manager = EventManager(self.database_path)
            manager_stats = event_manager.get_manager_stats()

            return {
                "database_path": self.database_path,
                "total_events": manager_stats.total_events,
                "dates_with_events": manager_stats.dates_with_events,
                "cached_events": manager_stats.cached_events,
                "cache_hit_rate": manager_stats.cache_hit_rate,
                "status_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "error": f"Failed to get migration status: {str(e)}",
                "status_timestamp": datetime.now().isoformat()
            }

    def __str__(self) -> str:
        """String representation of the migration helper."""
        return f"CalendarMigrationHelper(database_path='{self.database_path}')"

    def __repr__(self) -> str:
        """Detailed representation of the migration helper."""
        return f"CalendarMigrationHelper(database_path='{self.database_path}')"