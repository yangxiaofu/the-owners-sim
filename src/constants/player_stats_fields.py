"""
Player Statistics Field Names

Centralized enum system for standardizing player statistics field names across
the entire codebase. Eliminates naming convention inconsistencies between
simulation, persistence, and display layers.

This enum uses the simulation layer naming convention as the canonical standard.
All layers (simulation, persistence, database, display) should use these names.
"""

from enum import Enum
from typing import List, Set, Dict


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
    Canonical player statistics field names.

    Uses simulation layer naming convention as the standard.
    All code should reference these enum values instead of hard-coded strings.
    """

    # Basic player info (not stats, but needed for consistency)
    PLAYER_NAME = "player_name"
    PLAYER_NUMBER = "player_number"
    POSITION = "position"
    TEAM_ID = "team_id"
    PLAYER_ID = "player_id"

    # Rushing stats
    CARRIES = "rushing_attempts"  # Database-compatible name
    RUSHING_YARDS = "rushing_yards"
    RUSHING_TOUCHDOWNS = "rushing_tds"  # Database-compatible name

    # Passing stats (QB)
    PASS_ATTEMPTS = "passing_attempts"  # Database-compatible name
    COMPLETIONS = "passing_completions"  # Database-compatible name
    PASSING_YARDS = "passing_yards"
    PASSING_TDS = "passing_tds"
    INTERCEPTIONS_THROWN = "interceptions_thrown"
    SACKS_TAKEN = "sacks_taken"
    SACK_YARDS_LOST = "sack_yards_lost"
    QB_HITS_TAKEN = "qb_hits_taken"
    PRESSURES_FACED = "pressures_faced"
    AIR_YARDS = "air_yards"
    PASSING_TOUCHDOWNS = "passing_touchdowns"  # For non-QBs throwing TDs

    # Receiving stats (WR/TE)
    TARGETS = "targets"
    RECEPTIONS = "receptions"
    RECEIVING_YARDS = "receiving_yards"
    RECEIVING_TDS = "receiving_tds"
    DROPS = "drops"
    YAC = "yac"

    # Blocking stats (OL)
    BLOCKS_MADE = "blocks_made"
    BLOCKS_MISSED = "blocks_missed"
    PASS_BLOCKS = "pass_blocks"
    PRESSURES_ALLOWED = "pressures_allowed"
    SACKS_ALLOWED = "sacks_allowed"

    # Defensive stats
    TACKLES = "tackles"
    ASSISTED_TACKLES = "assisted_tackles"
    SACKS = "sacks"
    TACKLES_FOR_LOSS = "tackles_for_loss"
    QB_HITS = "qb_hits"
    QB_PRESSURES = "qb_pressures"
    QB_HURRIES = "qb_hurries"

    # Pass defense stats
    PASSES_DEFENDED = "passes_defended"
    PASSES_DEFLECTED = "passes_deflected"
    TIPPED_PASSES = "tipped_passes"
    INTERCEPTIONS = "interceptions"
    FORCED_FUMBLES = "forced_fumbles"

    # Special teams stats
    FIELD_GOAL_ATTEMPTS = "field_goal_attempts"
    FIELD_GOALS_MADE = "field_goals_made"
    FIELD_GOALS_MISSED = "field_goals_missed"
    FIELD_GOALS_BLOCKED = "field_goals_blocked"
    LONGEST_FIELD_GOAL = "longest_field_goal"
    FIELD_GOAL_HOLDS = "field_goal_holds"
    LONG_SNAPS = "long_snaps"
    SPECIAL_TEAMS_SNAPS = "special_teams_snaps"
    BLOCKS_ALLOWED = "blocks_allowed"

    # Extra point stats
    EXTRA_POINTS_MADE = "extra_points_made"
    EXTRA_POINTS_ATTEMPTED = "extra_points_attempted"

    # Penalty stats
    PENALTIES = "penalties"
    PENALTY_YARDS = "penalty_yards"

    @property
    def field_name(self) -> str:
        """Get the canonical field name"""
        return self.value

    @classmethod
    def all_fields(cls) -> List[str]:
        """Get all field names as a list"""
        return [field.value for field in cls]

    @classmethod
    def get_stat_fields(cls) -> Set[str]:
        """Get only statistical fields (exclude player info fields)"""
        info_fields = {cls.PLAYER_NAME.value, cls.PLAYER_NUMBER.value,
                      cls.POSITION.value, cls.TEAM_ID.value, cls.PLAYER_ID.value}
        return set(cls.all_fields()) - info_fields

    @classmethod
    def get_fields_by_category(cls, category: StatCategory) -> List[str]:
        """Get fields for a specific category"""
        category_mappings = {
            StatCategory.PASSING: [
                cls.PASS_ATTEMPTS, cls.COMPLETIONS, cls.PASSING_YARDS, cls.PASSING_TDS,
                cls.INTERCEPTIONS_THROWN, cls.SACKS_TAKEN, cls.SACK_YARDS_LOST,
                cls.QB_HITS_TAKEN, cls.PRESSURES_FACED, cls.AIR_YARDS, cls.PASSING_TOUCHDOWNS
            ],
            StatCategory.RUSHING: [
                cls.CARRIES, cls.RUSHING_YARDS, cls.RUSHING_TOUCHDOWNS
            ],
            StatCategory.RECEIVING: [
                cls.TARGETS, cls.RECEPTIONS, cls.RECEIVING_YARDS, cls.RECEIVING_TDS,
                cls.DROPS, cls.YAC
            ],
            StatCategory.DEFENSIVE: [
                cls.TACKLES, cls.ASSISTED_TACKLES, cls.SACKS, cls.TACKLES_FOR_LOSS,
                cls.QB_HITS, cls.QB_PRESSURES, cls.QB_HURRIES, cls.PASSES_DEFENDED,
                cls.PASSES_DEFLECTED, cls.TIPPED_PASSES, cls.INTERCEPTIONS, cls.FORCED_FUMBLES
            ],
            StatCategory.SPECIAL_TEAMS: [
                cls.FIELD_GOAL_ATTEMPTS, cls.FIELD_GOALS_MADE, cls.FIELD_GOALS_MISSED,
                cls.FIELD_GOALS_BLOCKED, cls.LONGEST_FIELD_GOAL, cls.FIELD_GOAL_HOLDS,
                cls.LONG_SNAPS, cls.SPECIAL_TEAMS_SNAPS, cls.BLOCKS_ALLOWED,
                cls.EXTRA_POINTS_MADE, cls.EXTRA_POINTS_ATTEMPTED
            ],
            StatCategory.BLOCKING: [
                cls.BLOCKS_MADE, cls.BLOCKS_MISSED, cls.PASS_BLOCKS,
                cls.PRESSURES_ALLOWED, cls.SACKS_ALLOWED
            ],
            StatCategory.PENALTIES: [
                cls.PENALTIES, cls.PENALTY_YARDS
            ]
        }

        return [field.value for field in category_mappings.get(category, [])]

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
            "pass_attempts": cls.PASS_ATTEMPTS.value,  # "pass_attempts" -> "passing_attempts"
            "completions": cls.COMPLETIONS.value,  # "completions" -> "passing_completions"
            "carries": cls.CARRIES.value,  # "carries" -> "rushing_attempts"
            "rushing_touchdowns": cls.RUSHING_TOUCHDOWNS.value,  # "rushing_touchdowns" -> "rushing_tds"

            # Persistence layer legacy names -> canonical names
            "passing_interceptions": cls.INTERCEPTIONS_THROWN.value,
            "pass_deflections": cls.PASSES_DEFENDED.value,
            "field_goals_attempted": cls.FIELD_GOAL_ATTEMPTS.value,

            # Add other legacy mappings as discovered
        }

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        """
        Get human-readable display names for UI/reports.

        Maps canonical field names to user-friendly display names.
        """
        return {
            cls.FIELD_GOAL_ATTEMPTS.value: "FG Attempts",
            cls.FIELD_GOALS_MADE.value: "FG Made",
            cls.EXTRA_POINTS_MADE.value: "XP Made",
            cls.EXTRA_POINTS_ATTEMPTED.value: "XP Attempts",
            cls.INTERCEPTIONS_THROWN.value: "Interceptions",
            cls.RUSHING_TOUCHDOWNS.value: "Rushing TDs",
            cls.PASSES_DEFENDED.value: "Pass Deflections",
            cls.PASSING_YARDS.value: "Pass Yards",
            cls.RUSHING_YARDS.value: "Rush Yards",
            cls.RECEIVING_YARDS.value: "Rec Yards",
            cls.TACKLES.value: "Tackles",
            cls.SACKS.value: "Sacks",
            cls.RECEPTIONS.value: "Receptions",
            cls.TARGETS.value: "Targets",
            cls.COMPLETIONS.value: "Completions",
            cls.PASS_ATTEMPTS.value: "Pass Attempts",
            cls.CARRIES.value: "Carries",
            # Add more display names as needed
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