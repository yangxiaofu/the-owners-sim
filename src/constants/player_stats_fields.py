"""
Player Statistics Field Names

Centralized enum system for standardizing player statistics field names across
the entire codebase. Eliminates naming convention inconsistencies between
simulation, persistence, and display layers.

This enum uses the simulation layer naming convention as the canonical standard.
All layers (simulation, persistence, database, display) should use these names.

Extended with database persistence metadata to auto-generate INSERT statements
and ensure consistency across all persistence layers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Set, Dict, Any, Optional


@dataclass(frozen=True)
class StatFieldMetadata:
    """
    Metadata for a player statistic field.

    Attributes:
        field_name: Canonical simulation layer name (e.g., "passing_yards")
        db_column: Database column name (e.g., "passing_yards")
        default_value: Default value for this stat (0 for numbers, "" for strings)
        data_type: Python type (int, float, str)
        persistable: Whether this field is saved to the database
    """
    field_name: str
    db_column: str
    default_value: Any
    data_type: type
    persistable: bool = True


class StatCategory(Enum):
    """Categories for organizing player statistics"""
    PASSING = "passing"
    RUSHING = "rushing"
    RECEIVING = "receiving"
    DEFENSIVE = "defensive"
    SPECIAL_TEAMS = "special_teams"
    BLOCKING = "blocking"
    PENALTIES = "penalties"


class PlayerStatField(Enum):
    """
    Canonical player statistics field names with database persistence metadata.

    Each field contains:
    - field_name: Simulation layer canonical name
    - db_column: Database column name
    - default_value: Default value when stat is not recorded
    - data_type: Python type for validation
    - persistable: Whether this stat is saved to database

    All code should reference these enum values instead of hard-coded strings.
    """

    # ============================================================
    # PLAYER IDENTIFICATION (Required for all records)
    # ============================================================
    PLAYER_ID = StatFieldMetadata("player_id", "player_id", "unknown", str, persistable=True)
    PLAYER_NAME = StatFieldMetadata("player_name", "player_name", "Unknown Player", str, persistable=True)
    TEAM_ID = StatFieldMetadata("team_id", "team_id", 0, int, persistable=True)
    POSITION = StatFieldMetadata("position", "position", "UNK", str, persistable=True)
    PLAYER_NUMBER = StatFieldMetadata("player_number", "player_number", 0, int, persistable=False)

    # ============================================================
    # PASSING STATS (QB) - Columns 7-11 in player_game_stats
    # ============================================================
    PASSING_YARDS = StatFieldMetadata("passing_yards", "passing_yards", 0, int, persistable=True)
    PASSING_TDS = StatFieldMetadata("passing_tds", "passing_tds", 0, int, persistable=True)
    COMPLETIONS = StatFieldMetadata("passing_completions", "passing_completions", 0, int, persistable=True)
    PASS_ATTEMPTS = StatFieldMetadata("passing_attempts", "passing_attempts", 0, int, persistable=True)
    INTERCEPTIONS_THROWN = StatFieldMetadata("interceptions_thrown", "passing_interceptions", 0, int, persistable=True)

    # Advanced passing stats (not yet in database schema)
    SACKS_TAKEN = StatFieldMetadata("sacks_taken", "sacks_taken", 0, int, persistable=False)
    SACK_YARDS_LOST = StatFieldMetadata("sack_yards_lost", "sack_yards_lost", 0, int, persistable=False)
    QB_HITS_TAKEN = StatFieldMetadata("qb_hits_taken", "qb_hits_taken", 0, int, persistable=False)
    PRESSURES_FACED = StatFieldMetadata("pressures_faced", "pressures_faced", 0, int, persistable=False)
    AIR_YARDS = StatFieldMetadata("air_yards", "air_yards", 0, int, persistable=False)
    PASSING_TOUCHDOWNS = StatFieldMetadata("passing_touchdowns", "passing_touchdowns", 0, int, persistable=False)

    # ============================================================
    # RUSHING STATS - Columns 12-14 in player_game_stats
    # ============================================================
    RUSHING_YARDS = StatFieldMetadata("rushing_yards", "rushing_yards", 0, int, persistable=True)
    RUSHING_TOUCHDOWNS = StatFieldMetadata("rushing_tds", "rushing_tds", 0, int, persistable=True)
    CARRIES = StatFieldMetadata("rushing_attempts", "rushing_attempts", 0, int, persistable=True)
    RUSHING_LONG = StatFieldMetadata("rushing_long", "rushing_long", 0, int, persistable=True)
    RUSHING_20_PLUS = StatFieldMetadata("rushing_20_plus", "rushing_20_plus", 0, int, persistable=True)
    RUSHING_FUMBLES = StatFieldMetadata("rushing_fumbles", "rushing_fumbles", 0, int, persistable=True)
    FUMBLES_LOST = StatFieldMetadata("fumbles_lost", "fumbles_lost", 0, int, persistable=True)
    YARDS_AFTER_CONTACT = StatFieldMetadata("yards_after_contact", "yards_after_contact", 0, int, persistable=True)

    # ============================================================
    # RECEIVING STATS (WR/TE) - Columns 15-18 in player_game_stats
    # ============================================================
    RECEIVING_YARDS = StatFieldMetadata("receiving_yards", "receiving_yards", 0, int, persistable=True)
    RECEIVING_TDS = StatFieldMetadata("receiving_tds", "receiving_tds", 0, int, persistable=True)
    RECEPTIONS = StatFieldMetadata("receptions", "receptions", 0, int, persistable=True)
    TARGETS = StatFieldMetadata("targets", "targets", 0, int, persistable=True)

    # Advanced receiving stats
    DROPS = StatFieldMetadata("drops", "receiving_drops", 0, int, persistable=True)
    YAC = StatFieldMetadata("yac", "yac", 0, int, persistable=False)
    RECEIVING_LONG = StatFieldMetadata("receiving_long", "receiving_long", 0, int, persistable=True)

    # ============================================================
    # DEFENSIVE STATS - Columns 19-21 in player_game_stats
    # ============================================================
    TACKLES = StatFieldMetadata("tackles", "tackles_total", 0, int, persistable=True)
    SACKS = StatFieldMetadata("sacks", "sacks", 0.0, float, persistable=True)
    INTERCEPTIONS = StatFieldMetadata("interceptions", "interceptions", 0, int, persistable=True)

    # Advanced defensive stats (not yet in database schema)
    ASSISTED_TACKLES = StatFieldMetadata("assisted_tackles", "assisted_tackles", 0, int, persistable=False)
    TACKLES_FOR_LOSS = StatFieldMetadata("tackles_for_loss", "tackles_for_loss", 0, int, persistable=False)
    QB_HITS = StatFieldMetadata("qb_hits", "qb_hits", 0, int, persistable=False)
    QB_PRESSURES = StatFieldMetadata("qb_pressures", "qb_pressures", 0, int, persistable=False)
    QB_HURRIES = StatFieldMetadata("qb_hurries", "qb_hurries", 0, int, persistable=False)
    PASSES_DEFENDED = StatFieldMetadata("passes_defended", "passes_defended", 0, int, persistable=False)
    PASSES_DEFLECTED = StatFieldMetadata("passes_deflected", "passes_deflected", 0, int, persistable=False)
    TIPPED_PASSES = StatFieldMetadata("tipped_passes", "tipped_passes", 0, int, persistable=False)
    FORCED_FUMBLES = StatFieldMetadata("forced_fumbles", "forced_fumbles", 0, int, persistable=False)

    # Coverage stats (DB/LB grading metrics)
    COVERAGE_TARGETS = StatFieldMetadata("coverage_targets", "coverage_targets", 0, int, persistable=True)
    COVERAGE_COMPLETIONS = StatFieldMetadata("coverage_completions", "coverage_completions", 0, int, persistable=True)
    COVERAGE_YARDS_ALLOWED = StatFieldMetadata("coverage_yards_allowed", "coverage_yards_allowed", 0, int, persistable=True)

    # Pass rush stats (DL grading metrics)
    PASS_RUSH_WINS = StatFieldMetadata("pass_rush_wins", "pass_rush_wins", 0, int, persistable=True)
    PASS_RUSH_ATTEMPTS = StatFieldMetadata("pass_rush_attempts", "pass_rush_attempts", 0, int, persistable=True)
    TIMES_DOUBLE_TEAMED = StatFieldMetadata("times_double_teamed", "times_double_teamed", 0, int, persistable=True)
    BLOCKING_ENCOUNTERS = StatFieldMetadata("blocking_encounters", "blocking_encounters", 0, int, persistable=True)

    # Ball carrier advanced stats (RB/WR grading)
    BROKEN_TACKLES = StatFieldMetadata("broken_tackles", "broken_tackles", 0, int, persistable=True)
    TACKLES_FACED = StatFieldMetadata("tackles_faced", "tackles_faced", 0, int, persistable=True)

    # QB advanced stats
    TIME_TO_THROW_TOTAL = StatFieldMetadata("time_to_throw_total", "time_to_throw_total", 0.0, float, persistable=True)
    THROW_COUNT = StatFieldMetadata("throw_count", "throw_count", 0, int, persistable=True)

    # ============================================================
    # SPECIAL TEAMS STATS - Columns 22-25 in player_game_stats
    # ============================================================
    FIELD_GOALS_MADE = StatFieldMetadata("field_goals_made", "field_goals_made", 0, int, persistable=True)
    FIELD_GOAL_ATTEMPTS = StatFieldMetadata("field_goal_attempts", "field_goals_attempted", 0, int, persistable=True)
    EXTRA_POINTS_MADE = StatFieldMetadata("extra_points_made", "extra_points_made", 0, int, persistable=True)
    EXTRA_POINTS_ATTEMPTED = StatFieldMetadata("extra_points_attempted", "extra_points_attempted", 0, int, persistable=True)

    # Advanced special teams stats (not yet in database schema)
    FIELD_GOALS_MISSED = StatFieldMetadata("field_goals_missed", "field_goals_missed", 0, int, persistable=False)
    FIELD_GOALS_BLOCKED = StatFieldMetadata("field_goals_blocked", "field_goals_blocked", 0, int, persistable=False)
    LONGEST_FIELD_GOAL = StatFieldMetadata("longest_field_goal", "longest_field_goal", 0, int, persistable=False)
    FIELD_GOAL_HOLDS = StatFieldMetadata("field_goal_holds", "field_goal_holds", 0, int, persistable=False)
    LONG_SNAPS = StatFieldMetadata("long_snaps", "long_snaps", 0, int, persistable=False)
    SPECIAL_TEAMS_SNAPS = StatFieldMetadata("special_teams_snaps", "special_teams_snaps", 0, int, persistable=False)
    BLOCKS_ALLOWED = StatFieldMetadata("blocks_allowed", "blocks_allowed", 0, int, persistable=False)

    # Distance-based FG tracking (for benchmark/analytics)
    FG_ATTEMPTS_0_39 = StatFieldMetadata("fg_attempts_0_39", "fg_attempts_0_39", 0, int, persistable=False)
    FG_MADE_0_39 = StatFieldMetadata("fg_made_0_39", "fg_made_0_39", 0, int, persistable=False)
    FG_ATTEMPTS_40_49 = StatFieldMetadata("fg_attempts_40_49", "fg_attempts_40_49", 0, int, persistable=False)
    FG_MADE_40_49 = StatFieldMetadata("fg_made_40_49", "fg_made_40_49", 0, int, persistable=False)
    FG_ATTEMPTS_50_PLUS = StatFieldMetadata("fg_attempts_50_plus", "fg_attempts_50_plus", 0, int, persistable=False)
    FG_MADE_50_PLUS = StatFieldMetadata("fg_made_50_plus", "fg_made_50_plus", 0, int, persistable=False)

    # Punting stats (Punter) - Added for box score display and persistence
    PUNTS = StatFieldMetadata("punts", "punts", 0, int, persistable=True)
    PUNT_YARDS = StatFieldMetadata("punt_yards", "punt_yards", 0, int, persistable=True)
    NET_PUNT_YARDS = StatFieldMetadata("net_punt_yards", "net_punt_yards", 0, int, persistable=True)
    LONG_PUNT = StatFieldMetadata("long_punt", "long_punt", 0, int, persistable=True)
    PUNTS_INSIDE_20 = StatFieldMetadata("punts_inside_20", "punts_inside_20", 0, int, persistable=True)
    PUNTS_TOUCHBACK = StatFieldMetadata("punts_touchback", "punts_touchback", 0, int, persistable=False)
    PUNTS_BLOCKED = StatFieldMetadata("punts_blocked", "punts_blocked", 0, int, persistable=False)
    PUNT_RETURNS = StatFieldMetadata("punt_returns", "punt_returns", 0, int, persistable=False)
    PUNT_RETURN_YARDS = StatFieldMetadata("punt_return_yards", "punt_return_yards", 0, int, persistable=False)
    FAIR_CATCHES = StatFieldMetadata("fair_catches", "fair_catches", 0, int, persistable=False)

    # ============================================================
    # SNAP TRACKING (Playing Time) - Columns 26-27 in player_game_stats
    # ============================================================
    OFFENSIVE_SNAPS = StatFieldMetadata("offensive_snaps", "snap_counts_offense", 0, int, persistable=True)
    DEFENSIVE_SNAPS = StatFieldMetadata("defensive_snaps", "snap_counts_defense", 0, int, persistable=True)
    TOTAL_SNAPS = StatFieldMetadata("total_snaps", "total_snaps", 0, int, persistable=False)

    # ============================================================
    # BLOCKING STATS (Offensive Line)
    # ============================================================
    BLOCKS_MADE = StatFieldMetadata("blocks_made", "blocks_made", 0, int, persistable=False)
    BLOCKS_MISSED = StatFieldMetadata("blocks_missed", "blocks_missed", 0, int, persistable=False)
    PASS_BLOCKS = StatFieldMetadata("pass_blocks", "pass_blocks", 0, int, persistable=True)
    PRESSURES_ALLOWED = StatFieldMetadata("pressures_allowed", "pressures_allowed", 0, int, persistable=True)
    SACKS_ALLOWED = StatFieldMetadata("sacks_allowed", "sacks_allowed", 0, int, persistable=True)
    PANCAKES = StatFieldMetadata("pancakes", "pancakes", 0, int, persistable=True)
    HURRIES_ALLOWED = StatFieldMetadata("hurries_allowed", "hurries_allowed", 0, int, persistable=True)
    RUN_BLOCKING_GRADE = StatFieldMetadata("run_blocking_grade", "run_blocking_grade", 0.0, float, persistable=False)
    PASS_BLOCKING_EFFICIENCY = StatFieldMetadata("pass_blocking_efficiency", "pass_blocking_efficiency", 0.0, float, persistable=False)
    MISSED_ASSIGNMENTS = StatFieldMetadata("missed_assignments", "missed_assignments", 0, int, persistable=False)
    HOLDING_PENALTIES = StatFieldMetadata("holding_penalties", "holding_penalties", 0, int, persistable=False)
    FALSE_START_PENALTIES = StatFieldMetadata("false_start_penalties", "false_start_penalties", 0, int, persistable=False)
    DOWNFIELD_BLOCKS = StatFieldMetadata("downfield_blocks", "downfield_blocks", 0, int, persistable=False)
    DOUBLE_TEAM_BLOCKS = StatFieldMetadata("double_team_blocks", "double_team_blocks", 0, int, persistable=False)
    CHIP_BLOCKS = StatFieldMetadata("chip_blocks", "chip_blocks", 0, int, persistable=False)

    # ============================================================
    # PENALTY STATS - Not yet in database schema
    # ============================================================
    PENALTIES = StatFieldMetadata("penalties", "penalties", 0, int, persistable=False)
    PENALTY_YARDS = StatFieldMetadata("penalty_yards", "penalty_yards", 0, int, persistable=False)

    # ============================================================
    # PROPERTY ACCESSORS
    # ============================================================

    @property
    def field_name(self) -> str:
        """Get the canonical simulation layer field name"""
        return self.value.field_name

    @property
    def db_column(self) -> str:
        """Get the database column name"""
        return self.value.db_column

    @property
    def default_value(self) -> Any:
        """Get the default value for this stat"""
        return self.value.default_value

    @property
    def data_type(self) -> type:
        """Get the Python type for this stat"""
        return self.value.data_type

    @property
    def persistable(self) -> bool:
        """Check if this stat is saved to database"""
        return self.value.persistable

    # ============================================================
    # CLASS METHODS FOR FIELD DISCOVERY
    # ============================================================

    @classmethod
    def all_fields(cls) -> List[str]:
        """Get all field names as a list"""
        return [field.field_name for field in cls]

    @classmethod
    def get_stat_fields(cls) -> Set[str]:
        """Get only statistical fields (exclude player info fields)"""
        info_fields = {cls.PLAYER_NAME.field_name, cls.PLAYER_NUMBER.field_name,
                      cls.POSITION.field_name, cls.TEAM_ID.field_name, cls.PLAYER_ID.field_name}
        return set(cls.all_fields()) - info_fields

    @classmethod
    def get_persistable_fields(cls) -> List['PlayerStatField']:
        """Get all fields that are saved to the database (in correct INSERT order)"""
        return [field for field in cls if field.persistable]

    @classmethod
    def get_persistable_field_names(cls) -> List[str]:
        """Get field names for all persistable fields"""
        return [field.field_name for field in cls.get_persistable_fields()]

    @classmethod
    def get_persistable_db_columns(cls) -> List[str]:
        """Get database column names for all persistable fields (in correct INSERT order)"""
        return [field.db_column for field in cls.get_persistable_fields()]

    @classmethod
    def get_fields_by_category(cls, category: StatCategory) -> List[str]:
        """Get fields for a specific category"""
        category_mappings = {
            StatCategory.PASSING: [
                cls.PASS_ATTEMPTS, cls.COMPLETIONS, cls.PASSING_YARDS, cls.PASSING_TDS,
                cls.INTERCEPTIONS_THROWN, cls.SACKS_TAKEN, cls.SACK_YARDS_LOST,
                cls.QB_HITS_TAKEN, cls.PRESSURES_FACED, cls.AIR_YARDS, cls.PASSING_TOUCHDOWNS,
                # QB advanced stats
                cls.TIME_TO_THROW_TOTAL, cls.THROW_COUNT
            ],
            StatCategory.RUSHING: [
                cls.CARRIES, cls.RUSHING_YARDS, cls.RUSHING_TOUCHDOWNS, cls.RUSHING_LONG,
                cls.RUSHING_20_PLUS, cls.RUSHING_FUMBLES, cls.FUMBLES_LOST, cls.YARDS_AFTER_CONTACT,
                # Ball carrier advanced stats
                cls.BROKEN_TACKLES, cls.TACKLES_FACED
            ],
            StatCategory.RECEIVING: [
                cls.TARGETS, cls.RECEPTIONS, cls.RECEIVING_YARDS, cls.RECEIVING_TDS,
                cls.DROPS, cls.YAC
            ],
            StatCategory.DEFENSIVE: [
                cls.TACKLES, cls.ASSISTED_TACKLES, cls.SACKS, cls.TACKLES_FOR_LOSS,
                cls.QB_HITS, cls.QB_PRESSURES, cls.QB_HURRIES, cls.PASSES_DEFENDED,
                cls.PASSES_DEFLECTED, cls.TIPPED_PASSES, cls.INTERCEPTIONS, cls.FORCED_FUMBLES,
                # Coverage stats (DB/LB grading)
                cls.COVERAGE_TARGETS, cls.COVERAGE_COMPLETIONS, cls.COVERAGE_YARDS_ALLOWED,
                # Pass rush stats (DL grading)
                cls.PASS_RUSH_WINS, cls.PASS_RUSH_ATTEMPTS, cls.TIMES_DOUBLE_TEAMED, cls.BLOCKING_ENCOUNTERS
            ],
            StatCategory.SPECIAL_TEAMS: [
                cls.FIELD_GOAL_ATTEMPTS, cls.FIELD_GOALS_MADE, cls.FIELD_GOALS_MISSED,
                cls.FIELD_GOALS_BLOCKED, cls.LONGEST_FIELD_GOAL, cls.FIELD_GOAL_HOLDS,
                cls.LONG_SNAPS, cls.SPECIAL_TEAMS_SNAPS, cls.BLOCKS_ALLOWED,
                cls.EXTRA_POINTS_MADE, cls.EXTRA_POINTS_ATTEMPTED,
                # Punting stats
                cls.PUNTS, cls.PUNT_YARDS, cls.NET_PUNT_YARDS, cls.LONG_PUNT,
                cls.PUNTS_INSIDE_20, cls.PUNTS_TOUCHBACK, cls.PUNTS_BLOCKED,
                cls.PUNT_RETURNS, cls.PUNT_RETURN_YARDS, cls.FAIR_CATCHES
            ],
            StatCategory.BLOCKING: [
                cls.BLOCKS_MADE, cls.BLOCKS_MISSED, cls.PASS_BLOCKS,
                cls.PRESSURES_ALLOWED, cls.SACKS_ALLOWED,
                # Advanced blocking stats
                cls.PANCAKES, cls.HURRIES_ALLOWED,
                cls.RUN_BLOCKING_GRADE, cls.PASS_BLOCKING_EFFICIENCY,
                cls.MISSED_ASSIGNMENTS, cls.HOLDING_PENALTIES,
                cls.FALSE_START_PENALTIES, cls.DOWNFIELD_BLOCKS,
                cls.DOUBLE_TEAM_BLOCKS, cls.CHIP_BLOCKS
            ],
            StatCategory.PENALTIES: [
                cls.PENALTIES, cls.PENALTY_YARDS
            ]
        }

        return [field.field_name for field in category_mappings.get(category, [])]

    @classmethod
    def validate_field_name(cls, field_name: str) -> bool:
        """Validate that a field name is a recognized player stat field"""
        return field_name in cls.all_fields()

    @classmethod
    def get_legacy_mapping(cls) -> Dict[str, str]:
        """
        Mapping from legacy naming conventions to canonical names.

        This helps with migration from the old inconsistent naming.
        Eventually this should be removed once all code uses the enum.
        """
        return {
            # Old simulation layer names -> new database-compatible names
            "pass_attempts": cls.PASS_ATTEMPTS.field_name,
            "completions": cls.COMPLETIONS.field_name,
            "carries": cls.CARRIES.field_name,
            "rushing_touchdowns": cls.RUSHING_TOUCHDOWNS.field_name,

            # Persistence layer legacy names -> canonical names
            "passing_interceptions": cls.INTERCEPTIONS_THROWN.field_name,
            "pass_deflections": cls.PASSES_DEFENDED.field_name,
            "field_goals_attempted": cls.FIELD_GOAL_ATTEMPTS.field_name,

            # Add other legacy mappings as discovered
        }

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        """
        Get human-readable display names for UI/reports.

        Maps canonical field names to user-friendly display names.
        """
        return {
            cls.FIELD_GOAL_ATTEMPTS.field_name: "FG Attempts",
            cls.FIELD_GOALS_MADE.field_name: "FG Made",
            cls.EXTRA_POINTS_MADE.field_name: "XP Made",
            cls.EXTRA_POINTS_ATTEMPTED.field_name: "XP Attempts",
            cls.INTERCEPTIONS_THROWN.field_name: "Interceptions",
            cls.RUSHING_TOUCHDOWNS.field_name: "Rushing TDs",
            cls.PASSES_DEFENDED.field_name: "Pass Deflections",
            cls.PASSING_YARDS.field_name: "Pass Yards",
            cls.RUSHING_YARDS.field_name: "Rush Yards",
            cls.RECEIVING_YARDS.field_name: "Rec Yards",
            cls.TACKLES.field_name: "Tackles",
            cls.SACKS.field_name: "Sacks",
            cls.RECEPTIONS.field_name: "Receptions",
            cls.TARGETS.field_name: "Targets",
            cls.COMPLETIONS.field_name: "Completions",
            cls.PASS_ATTEMPTS.field_name: "Pass Attempts",
            cls.CARRIES.field_name: "Carries",
            # Punt stats
            cls.PUNTS.field_name: "Punts",
            cls.PUNT_YARDS.field_name: "Punt Yards",
            cls.NET_PUNT_YARDS.field_name: "Net Punt Yards",
            cls.LONG_PUNT.field_name: "Long Punt",
            cls.PUNTS_INSIDE_20.field_name: "Inside 20",
            cls.PUNTS_TOUCHBACK.field_name: "Touchbacks",
            cls.PUNT_RETURNS.field_name: "Punt Returns",
            cls.PUNT_RETURN_YARDS.field_name: "PR Yards",
            cls.FAIR_CATCHES.field_name: "Fair Catches",
        }

    # ============================================================
    # DATABASE PERSISTENCE HELPERS (Phase 1 Complete)
    # ============================================================

    @classmethod
    def generate_insert_statement(
        cls,
        table_name: str = "player_game_stats",
        additional_columns: Optional[List[str]] = None
    ) -> str:
        """
        Auto-generate INSERT statement for player stats persistence.

        Args:
            table_name: Database table name (default: "player_game_stats")
            additional_columns: Extra columns to include (e.g., ["dynasty_id", "game_id"])

        Returns:
            SQL INSERT statement with proper column ordering

        Example:
            >>> stmt = PlayerStatField.generate_insert_statement(
            ...     additional_columns=["dynasty_id", "game_id"]
            ... )
            >>> print(stmt)
            INSERT INTO player_game_stats (
                dynasty_id, game_id, player_id, player_name, ...
            ) VALUES (?, ?, ?, ?, ...)
        """
        # Build column list: additional columns + persistable fields
        columns = list(additional_columns) if additional_columns else []
        columns.extend(cls.get_persistable_db_columns())

        # Generate placeholders (? for each column)
        placeholders = ", ".join(["?" for _ in columns])

        # Format column names (indented, comma-separated)
        column_list = ",\n        ".join(columns)

        # Build complete INSERT statement
        query = f"""
    INSERT INTO {table_name} (
        {column_list}
    ) VALUES ({placeholders})
"""
        return query.strip()

    @classmethod
    def extract_params_from_stats(
        cls,
        player_stat,
        additional_params: Optional[tuple] = None
    ) -> tuple:
        """
        Extract database parameter values from a PlayerStats object.

        Args:
            player_stat: PlayerStats object with accumulated stats
            additional_params: Extra params to prepend (e.g., (dynasty_id, game_id))

        Returns:
            Tuple of values in correct order for INSERT statement

        Example:
            >>> from play_engine.simulation.stats import PlayerStats
            >>> stats = PlayerStats(...)
            >>> params = PlayerStatField.extract_params_from_stats(
            ...     stats,
            ...     additional_params=("dynasty_1", "game_123")
            ... )
            >>> # params = ("dynasty_1", "game_123", "player_id", "Player Name", ...)
        """
        # Start with additional params if provided
        params = list(additional_params) if additional_params else []

        # Extract values for each persistable field
        for field in cls.get_persistable_fields():
            value = getattr(player_stat, field.field_name, field.default_value)
            params.append(value)

        return tuple(params)

    @classmethod
    def validate_schema_consistency(cls, database_columns: List[str]) -> Dict[str, Any]:
        """
        Validate that database schema matches the defined persistable fields.

        Args:
            database_columns: List of column names from database schema

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "missing_in_db": List[str],  # Fields defined but not in DB
                "extra_in_db": List[str],    # Columns in DB but not defined
                "errors": List[str]           # Human-readable error messages
            }

        Example:
            >>> result = PlayerStatField.validate_schema_consistency(
            ...     database_columns=["player_id", "player_name", "passing_yards"]
            ... )
            >>> if not result["valid"]:
            ...     for error in result["errors"]:
            ...         print(f"Schema Error: {error}")
        """
        expected_columns = set(cls.get_persistable_db_columns())
        actual_columns = set(database_columns)

        missing_in_db = expected_columns - actual_columns
        extra_in_db = actual_columns - expected_columns

        errors = []
        if missing_in_db:
            errors.append(f"Missing columns in database: {', '.join(sorted(missing_in_db))}")
        if extra_in_db:
            errors.append(f"Extra columns in database: {', '.join(sorted(extra_in_db))}")

        return {
            "valid": len(errors) == 0,
            "missing_in_db": sorted(missing_in_db),
            "extra_in_db": sorted(extra_in_db),
            "errors": errors
        }


# Convenience constants for commonly used field sets
OFFENSIVE_STATS = (
    PlayerStatField.get_fields_by_category(StatCategory.PASSING) +
    PlayerStatField.get_fields_by_category(StatCategory.RUSHING) +
    PlayerStatField.get_fields_by_category(StatCategory.RECEIVING)
)

DEFENSIVE_STATS = PlayerStatField.get_fields_by_category(StatCategory.DEFENSIVE)

SPECIAL_TEAMS_STATS = PlayerStatField.get_fields_by_category(StatCategory.SPECIAL_TEAMS)

ALL_STAT_FIELDS = PlayerStatField.get_stat_fields()


def validate_player_stats_dict(stats_dict: Dict[str, any]) -> List[str]:
    """
    Validate a player statistics dictionary against the canonical field names.

    Args:
        stats_dict: Dictionary of player statistics

    Returns:
        List of invalid field names (empty if all valid)
    """
    invalid_fields = []
    for field_name in stats_dict.keys():
        if not PlayerStatField.validate_field_name(field_name):
            invalid_fields.append(field_name)
    return invalid_fields


def migrate_legacy_field_name(legacy_name: str) -> str:
    """
    Convert a legacy field name to the canonical name.

    Args:
        legacy_name: Old field name from persistence layer

    Returns:
        Canonical field name, or original name if no mapping exists
    """
    legacy_mapping = PlayerStatField.get_legacy_mapping()
    return legacy_mapping.get(legacy_name, legacy_name)