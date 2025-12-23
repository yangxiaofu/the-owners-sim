"""
Schema Generator for Player Stats Persistence

Auto-generates SQL INSERT statements and parameter tuples from PlayerStatField metadata.
Ensures consistency across all persistence layers (DailyDataPersister, DatabaseDemoPersister).

Phase 2 of the scalable stats persistence architecture.

Usage:
    >>> from persistence.schema_generator import generate_player_stats_insert, extract_player_stats_params
    >>>
    >>> # Generate INSERT statement
    >>> query = generate_player_stats_insert(
    ...     table_name="player_game_stats",
    ...     additional_columns=["dynasty_id", "game_id"]
    ... )
    >>>
    >>> # Extract params from PlayerStats object
    >>> params = extract_player_stats_params(
    ...     player_stat,
    ...     additional_values=(dynasty_id, game_id)
    ... )
    >>>
    >>> # Execute
    >>> cursor.execute(query, params)
"""

from typing import List, Optional, Tuple, Any
from constants.player_stats_fields import PlayerStatField


def generate_player_stats_insert(
    table_name: str = "player_game_stats",
    additional_columns: Optional[List[str]] = None
) -> str:
    """
    Generate INSERT statement for player stats persistence.

    Auto-generates SQL INSERT statement using PlayerStatField metadata.
    All persistable fields are included in correct order with proper column names.

    Args:
        table_name: Database table name (default: "player_game_stats")
        additional_columns: Extra columns to prepend (e.g., ["dynasty_id", "game_id"])

    Returns:
        Complete SQL INSERT statement with placeholders

    Example:
        >>> query = generate_player_stats_insert(
        ...     additional_columns=["dynasty_id", "game_id"]
        ... )
        >>> print(query)
        INSERT INTO player_game_stats (
            dynasty_id,
            game_id,
            player_id,
            player_name,
            ...
        ) VALUES (?, ?, ?, ?, ...)

    Note:
        This delegates to PlayerStatField.generate_insert_statement() for consistency.
    """
    return PlayerStatField.generate_insert_statement(
        table_name=table_name,
        additional_columns=additional_columns
    )


def extract_player_stats_params(
    player_stat,
    additional_values: Optional[Tuple[Any, ...]] = None
) -> Tuple[Any, ...]:
    """
    Extract parameter values from PlayerStats object for database insertion.

    Extracts all persistable field values in correct order matching the INSERT statement.
    Uses default values from PlayerStatField metadata for missing attributes.

    Args:
        player_stat: PlayerStats object with accumulated statistics
        additional_values: Extra values to prepend (e.g., (dynasty_id, game_id))

    Returns:
        Tuple of values in correct order for INSERT statement

    Example:
        >>> from play_engine.simulation.stats import PlayerStats
        >>>
        >>> stats = PlayerStats(
        ...     player_id="player_123",
        ...     player_name="Patrick Mahomes",
        ...     passing_yards=350,
        ...     passing_tds=3,
        ...     interceptions_thrown=1
        ... )
        >>>
        >>> params = extract_player_stats_params(
        ...     stats,
        ...     additional_values=("dynasty_1", "game_KC_vs_LV_2024_W1")
        ... )
        >>>
        >>> # params = ("dynasty_1", "game_KC_vs_LV_2024_W1", "player_123", "Patrick Mahomes", ...)

    Note:
        This delegates to PlayerStatField.extract_params_from_stats() for consistency.
    """
    return PlayerStatField.extract_params_from_stats(
        player_stat,
        additional_params=additional_values
    )


def get_persistable_field_count() -> int:
    """
    Get the number of persistable fields in the schema.

    Useful for validation and debugging.

    Returns:
        Count of fields that are saved to database

    Example:
        >>> count = get_persistable_field_count()
        >>> print(f"Expecting {count} values per player stat record")
    """
    return len(PlayerStatField.get_persistable_fields())


def get_persistable_column_names() -> List[str]:
    """
    Get list of database column names for all persistable fields.

    Returns columns in the same order they appear in INSERT statements.

    Returns:
        List of database column names

    Example:
        >>> columns = get_persistable_column_names()
        >>> print(f"Database columns: {', '.join(columns)}")
    """
    return PlayerStatField.get_persistable_db_columns()


def validate_database_schema(database_columns: List[str]) -> dict:
    """
    Validate that database schema matches PlayerStatField definitions.

    Compares actual database columns against expected persistable fields.
    Detects missing columns (in code but not DB) and extra columns (in DB but not code).

    Args:
        database_columns: List of column names from database schema
                         (e.g., from PRAGMA table_info)

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "missing_in_db": List[str],  # Defined in code but not in database
            "extra_in_db": List[str],    # In database but not defined in code
            "errors": List[str]           # Human-readable error messages
        }

    Example:
        >>> import sqlite3
        >>> conn = sqlite3.connect("data/database/nfl_simulation.db")
        >>> cursor = conn.cursor()
        >>> cursor.execute("PRAGMA table_info(player_game_stats)")
        >>> columns = [row[1] for row in cursor.fetchall()]
        >>>
        >>> result = validate_database_schema(columns)
        >>> if not result["valid"]:
        ...     print("Schema mismatch detected!")
        ...     for error in result["errors"]:
        ...         print(f"  ERROR: {error}")
        >>> else:
        ...     print("✅ Database schema is consistent with code definitions")
    """
    return PlayerStatField.validate_schema_consistency(database_columns)


# ============================================================
# HELPER FUNCTIONS FOR PERSISTER MIGRATION
# ============================================================

def get_insert_query_and_param_count(
    table_name: str = "player_game_stats",
    additional_columns: Optional[List[str]] = None
) -> Tuple[str, int]:
    """
    Get INSERT query and expected parameter count.

    Convenience function for persister setup and validation.

    Args:
        table_name: Database table name
        additional_columns: Extra columns to include

    Returns:
        Tuple of (query_string, expected_param_count)

    Example:
        >>> query, count = get_insert_query_and_param_count(
        ...     additional_columns=["dynasty_id", "game_id"]
        ... )
        >>> print(f"Query expects {count} parameters")
    """
    query = generate_player_stats_insert(table_name, additional_columns)
    param_count = len(additional_columns or []) + get_persistable_field_count()
    return query, param_count


def print_schema_info():
    """
    Print detailed schema information for debugging.

    Outputs all persistable fields with their database column mappings.
    Useful for understanding what fields will be saved.
    """
    print("=" * 80)
    print("PLAYER STATS PERSISTENCE SCHEMA")
    print("=" * 80)

    persistable = PlayerStatField.get_persistable_fields()
    print(f"\nTotal persistable fields: {len(persistable)}\n")

    print(f"{'Field Name':<30s} {'DB Column':<30s} {'Type':<10s} {'Default':<10s}")
    print("-" * 80)

    for field in persistable:
        type_name = field.data_type.__name__
        default_str = str(field.default_value)[:10]
        print(f"{field.field_name:<30s} {field.db_column:<30s} {type_name:<10s} {default_str:<10s}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run when script is executed directly
    print("Schema Generator - Diagnostic Mode\n")

    # Print schema info
    print_schema_info()

    # Show sample INSERT statement
    print("\nSample INSERT Statement:")
    print("-" * 80)
    query = generate_player_stats_insert(additional_columns=["dynasty_id", "game_id"])
    print(query)

    # Show parameter count
    _, count = get_insert_query_and_param_count(additional_columns=["dynasty_id", "game_id"])
    print(f"\n✅ Expected parameter count: {count}")
