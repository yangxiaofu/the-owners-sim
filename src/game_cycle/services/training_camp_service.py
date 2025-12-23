"""
Training Camp Service for Game Cycle.

Handles player attribute adjustments during the offseason training camp stage.
Implements age-weighted progression/regression with position-specific attributes.
Design prioritizes simplicity and replaceability for future player development enhancements.
"""

from typing import Dict, List, Any, Optional, Protocol
from dataclasses import dataclass, field
from enum import Enum
import logging
import sqlite3
import json
import random

from src.constants.position_normalizer import normalize_position
from src.game_cycle.database.progression_history_api import (
    ProgressionHistoryAPI, ProgressionHistoryRecord
)
from src.utils.player_field_extractors import extract_overall_rating


class AgeCategory(Enum):
    """Age brackets for development curves."""
    YOUNG = "young"          # Under 26: More likely to improve
    PRIME = "prime"          # 26-30: Stable/small changes
    VETERAN = "veteran"      # 31+: More likely to decline


@dataclass
class AttributeChange:
    """Represents a single attribute change."""
    attribute_name: str
    old_value: int
    new_value: int
    change: int  # new - old


@dataclass
class PlayerDevelopmentResult:
    """Result of training camp for a single player."""
    player_id: int
    player_name: str
    position: str
    age: int
    team_id: int
    age_category: AgeCategory
    old_overall: int
    new_overall: int
    overall_change: int
    attribute_changes: List[AttributeChange] = field(default_factory=list)
    potential: int = 99       # Player's ceiling rating
    dev_type: str = "N"       # Development curve: "E" (early), "N" (normal), "L" (late)


class DevelopmentAlgorithm(Protocol):
    """Protocol for pluggable development algorithms (future-proofing)."""

    def get_age_category(
        self,
        age: int,
        position: Optional[str] = None,
        archetype_id: Optional[str] = None
    ) -> AgeCategory:
        """Determine age category for a player."""
        ...

    def calculate_changes(
        self,
        age: int,
        position: str,
        current_attributes: Dict[str, Any],
        potential: Optional[int] = None,
        archetype_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Calculate attribute changes for a player.

        Args:
            age: Player's current age
            position: Player's primary position
            current_attributes: Dict of current attribute values
            potential: Player's potential ceiling (optional, defaults to 99)
            archetype_id: Player's archetype ID for development curve lookup (optional)

        Returns:
            Dict of attribute_name -> change value (can be positive, negative, or 0)
        """
        ...


class PositionPeakAges:
    """
    Centralized position-to-peak-age mapping for position-specific development.

    Maps specific positions (e.g., 'left_tackle', 'mike_linebacker') to
    position groups used in AgeCurveParameters (e.g., 'OFFENSIVE_LINE', 'LINEBACKER').
    """

    POSITION_TO_GROUP = {
        # Quarterbacks
        'quarterback': 'QUARTERBACK', 'qb': 'QUARTERBACK',
        # Running backs
        'running_back': 'RUNNING_BACK', 'halfback': 'RUNNING_BACK',
        'fullback': 'RUNNING_BACK', 'rb': 'RUNNING_BACK', 'fb': 'RUNNING_BACK',
        # Wide receivers
        'wide_receiver': 'WIDE_RECEIVER', 'wr': 'WIDE_RECEIVER',
        # Tight ends
        'tight_end': 'TIGHT_END', 'te': 'TIGHT_END',
        # Offensive line
        'left_tackle': 'OFFENSIVE_LINE', 'right_tackle': 'OFFENSIVE_LINE',
        'left_guard': 'OFFENSIVE_LINE', 'right_guard': 'OFFENSIVE_LINE',
        'center': 'OFFENSIVE_LINE', 'offensive_line': 'OFFENSIVE_LINE',
        'ot': 'OFFENSIVE_LINE', 'og': 'OFFENSIVE_LINE', 'c': 'OFFENSIVE_LINE',
        # Defensive line
        'defensive_end': 'DEFENSIVE_LINE', 'defensive_tackle': 'DEFENSIVE_LINE',
        'nose_tackle': 'DEFENSIVE_LINE', 'edge': 'DEFENSIVE_LINE',
        'de': 'DEFENSIVE_LINE', 'dt': 'DEFENSIVE_LINE', 'nt': 'DEFENSIVE_LINE',
        # Linebackers
        'linebacker': 'LINEBACKER', 'outside_linebacker': 'LINEBACKER',
        'inside_linebacker': 'LINEBACKER', 'mike_linebacker': 'LINEBACKER',
        'will_linebacker': 'LINEBACKER', 'sam_linebacker': 'LINEBACKER',
        'mlb': 'LINEBACKER', 'olb': 'LINEBACKER', 'ilb': 'LINEBACKER', 'lb': 'LINEBACKER',
        # Defensive backs
        'cornerback': 'DEFENSIVE_BACK', 'safety': 'DEFENSIVE_BACK',
        'free_safety': 'DEFENSIVE_BACK', 'strong_safety': 'DEFENSIVE_BACK',
        'cb': 'DEFENSIVE_BACK', 'fs': 'DEFENSIVE_BACK', 'ss': 'DEFENSIVE_BACK', 's': 'DEFENSIVE_BACK',
        # Special teams
        'kicker': 'KICKER', 'punter': 'PUNTER', 'long_snapper': 'OFFENSIVE_LINE',
        'k': 'KICKER', 'p': 'PUNTER', 'ls': 'OFFENSIVE_LINE',
    }

    @classmethod
    def get_position_group(cls, position: str) -> str:
        """Map a specific position to its AgeCurveParameters group."""
        key = normalize_position(position)
        return cls.POSITION_TO_GROUP.get(key, 'DEFAULT')

    @classmethod
    def get_peak_ages(cls, position: str) -> tuple:
        """
        Get (peak_start, peak_end) for a position.

        Returns:
            Tuple of (peak_start, peak_end) ages
        """
        from src.transactions.transaction_constants import AgeCurveParameters
        group = cls.get_position_group(position)
        params = getattr(AgeCurveParameters, group, AgeCurveParameters.DEFAULT)
        return params['peak_start'], params['peak_end']

    @classmethod
    def get_growth_rates(cls, position: str) -> tuple:
        """
        Get (growth_rate, regression_rate) for a position.

        Returns:
            Tuple of (growth_rate, regression_rate) - base points/year for development
        """
        from src.transactions.transaction_constants import AgeCurveParameters
        group = cls.get_position_group(position)
        params = getattr(AgeCurveParameters, group, AgeCurveParameters.DEFAULT)
        return params.get('growth_rate', 2.0), params.get('regression_rate', 2.0)


class AgeWeightedDevelopment:
    """
    Default development algorithm with age-weighted progression.

    - Young (< 26): 70% improve, 20% stable, 10% decline
    - Prime (26-30): 20% improve, 60% stable, 20% decline
    - Veteran (31+): 10% improve, 30% stable, 60% decline

    Implements DevelopmentAlgorithm protocol for easy replacement.
    """

    # Position-specific attributes that can change
    POSITION_ATTRIBUTES = {
        'quarterback': ['accuracy', 'arm_strength', 'awareness', 'mobility', 'pocket_presence'],
        'running_back': ['speed', 'agility', 'elusiveness', 'strength', 'awareness', 'carrying', 'vision'],
        'wide_receiver': ['speed', 'hands', 'route_running', 'agility', 'awareness', 'catching'],
        'tight_end': ['hands', 'blocking', 'route_running', 'speed', 'awareness', 'catching'],
        'left_tackle': ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'technique'],
        'right_tackle': ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'technique'],
        'left_guard': ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'technique'],
        'right_guard': ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'technique'],
        'center': ['pass_blocking', 'run_blocking', 'snap_timing', 'awareness', 'technique'],
        'defensive_end': ['pass_rush', 'run_defense', 'speed', 'strength', 'awareness', 'technique'],
        'defensive_tackle': ['pass_rush', 'run_defense', 'strength', 'awareness', 'technique'],
        'nose_tackle': ['run_defense', 'strength', 'awareness', 'technique'],
        'linebacker': ['coverage', 'run_defense', 'tackling', 'speed', 'awareness'],
        'outside_linebacker': ['pass_rush', 'coverage', 'tackling', 'speed', 'awareness'],
        'inside_linebacker': ['coverage', 'run_defense', 'tackling', 'awareness'],
        'mike_linebacker': ['coverage', 'run_defense', 'tackling', 'awareness'],
        'will_linebacker': ['coverage', 'run_defense', 'tackling', 'speed', 'awareness'],
        'sam_linebacker': ['coverage', 'run_defense', 'tackling', 'awareness'],
        'cornerback': ['coverage', 'speed', 'press', 'awareness', 'ball_skills'],
        'safety': ['coverage', 'range', 'tackling', 'awareness', 'speed'],
        'free_safety': ['coverage', 'range', 'speed', 'awareness', 'ball_skills'],
        'strong_safety': ['coverage', 'tackling', 'run_support', 'awareness'],
        'kicker': ['kick_power', 'kick_accuracy', 'awareness'],
        'punter': ['punt_power', 'punt_accuracy', 'awareness', 'hang_time'],
        'fullback': ['blocking', 'strength', 'awareness', 'carrying'],
        'long_snapper': ['snap_accuracy', 'awareness'],
    }

    # Age category boundaries
    YOUNG_MAX_AGE = 25
    PRIME_MAX_AGE = 30

    # Development probability weights by age category
    # (improve_chance, stable_chance, decline_chance) - must sum to 1.0
    AGE_WEIGHTS = {
        AgeCategory.YOUNG: (0.70, 0.20, 0.10),
        AgeCategory.PRIME: (0.20, 0.60, 0.20),
        AgeCategory.VETERAN: (0.10, 0.30, 0.60),
    }

    # Magnitude ranges for changes
    IMPROVE_RANGE = (1, 5)   # +1 to +5
    DECLINE_RANGE = (-5, -1)  # -1 to -5

    # Rating boundaries
    RATING_FLOOR = 40
    RATING_CEILING = 99
    DIMINISHING_RETURNS_THRESHOLD = 90

    def get_age_category(
        self,
        age: int,
        position: Optional[str] = None,
        archetype_id: Optional[str] = None
    ) -> AgeCategory:
        """
        Determine age category for a player using position-specific peak ages.

        Uses hierarchy:
        1. Archetype-specific peak ages (if archetype_id provided)
        2. Position-group peak ages (if position provided)
        3. Generic thresholds (fallback)

        Args:
            age: Player's current age
            position: Player's primary position (optional)
            archetype_id: Player's archetype ID for lookup (optional)

        Returns:
            AgeCategory enum value (YOUNG, PRIME, or VETERAN)
        """
        peak_start, peak_end = self._get_peak_ages(position, archetype_id)

        if age < peak_start:
            return AgeCategory.YOUNG
        elif age <= peak_end:
            return AgeCategory.PRIME
        else:
            return AgeCategory.VETERAN

    def _get_peak_ages(
        self,
        position: Optional[str],
        archetype_id: Optional[str]
    ) -> tuple:
        """
        Get peak age range using hierarchy: archetype > position > generic.

        Returns:
            Tuple of (peak_start, peak_end) ages
        """
        # Level 1: Try archetype-specific lookup
        if archetype_id:
            peak_ages = self._get_archetype_peak_ages(archetype_id)
            if peak_ages:
                return peak_ages

        # Level 2: Try position-group lookup
        if position:
            return PositionPeakAges.get_peak_ages(position)

        # Level 3: Fallback to generic thresholds (existing behavior)
        return (self.YOUNG_MAX_AGE + 1, self.PRIME_MAX_AGE)

    def _get_archetype_peak_ages(self, archetype_id: str) -> Optional[tuple]:
        """
        Look up peak ages from archetype registry.

        Returns None if archetype not found or registry not available.
        """
        try:
            from src.player_generation.archetypes.archetype_registry import ArchetypeRegistry
            registry = ArchetypeRegistry()
            archetype = registry.get_archetype(archetype_id)
            if archetype and hasattr(archetype, 'peak_age_range') and archetype.peak_age_range:
                return archetype.peak_age_range
        except Exception:
            # Gracefully handle missing registry or lookup failures
            pass
        return None

    def _get_archetype_development_curve(self, archetype_id: Optional[str]) -> str:
        """
        Look up development curve from archetype registry.

        Args:
            archetype_id: Player's archetype identifier

        Returns:
            Development curve type: "early", "normal", or "late".
            Defaults to "normal" if archetype not found.
        """
        if not archetype_id:
            return "normal"

        try:
            from src.player_generation.archetypes.archetype_registry import ArchetypeRegistry
            registry = ArchetypeRegistry()
            archetype = registry.get_archetype(archetype_id)
            if archetype and hasattr(archetype, 'development_curve') and archetype.development_curve:
                return archetype.development_curve
        except Exception:
            # Gracefully handle missing registry or lookup failures
            pass
        return "normal"

    def calculate_changes(
        self,
        age: int,
        position: str,
        current_attributes: Dict[str, Any],
        potential: Optional[int] = None,
        archetype_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Calculate attribute changes for a player using position-specific growth rates.

        Uses:
        - Position-specific growth/regression rates from AgeCurveParameters
        - Development curve modifiers from archetype (early/normal/late) - Tollgate 4
        - Attribute category parameters (physical/mental/technique) - Tollgate 5
        - Distance-to-peak multiplier (younger players further from peak grow faster)
        - Age-weighted probabilities for change direction
        - Individual potential ceiling to cap improvements (Tollgate 3)

        Args:
            age: Player's current age
            position: Player's primary position
            current_attributes: Dict of current attribute values
            potential: Player's potential ceiling (optional, defaults to RATING_CEILING)
            archetype_id: Player's archetype ID for development curve lookup (optional)

        Returns:
            Dict of attribute_name -> change value (can be positive, negative, or 0)
        """
        age_category = self.get_age_category(age, position, archetype_id)

        # Get position-specific parameters
        peak_start, peak_end = PositionPeakAges.get_peak_ages(position)
        growth_rate, regression_rate = PositionPeakAges.get_growth_rates(position)

        # Get development curve modifiers (Tollgate 4: Development Curve Integration)
        from src.transactions.transaction_constants import (
            DevelopmentCurveModifiers,
            AttributeCategoryParameters,
            get_attribute_category
        )
        development_curve = self._get_archetype_development_curve(archetype_id)
        curve_modifiers = DevelopmentCurveModifiers.get_modifiers(development_curve)

        # Calculate distance multiplier based on age category
        if age_category == AgeCategory.YOUNG:
            years_to_peak = peak_start - age
            # +10% per year away from peak, capped at +50%
            distance_multiplier = 1.0 + min(0.5, 0.1 * years_to_peak)
        elif age_category == AgeCategory.VETERAN:
            years_past_peak = age - peak_end
            # +10% per year past peak, capped at +50%
            distance_multiplier = 1.0 + min(0.5, 0.1 * years_past_peak)
        else:
            distance_multiplier = 1.0  # PRIME has no distance modifier

        # Get position-relevant attributes
        position_key = normalize_position(position)
        relevant_attrs = self.POSITION_ATTRIBUTES.get(position_key, ['awareness'])

        # Map age category to string for AttributeCategoryParameters lookup
        age_category_str = {
            AgeCategory.YOUNG: "young",
            AgeCategory.PRIME: "prime",
            AgeCategory.VETERAN: "veteran"
        }[age_category]

        changes = {}

        for attr in relevant_attrs:
            if attr not in current_attributes:
                continue

            current_value = current_attributes[attr]
            if not isinstance(current_value, (int, float)):
                continue

            current_value = int(current_value)

            # Tollgate 5: Get attribute category and category-specific parameters
            attr_category = get_attribute_category(attr)
            cat_params = AttributeCategoryParameters.get_params(
                attr_category, age_category_str, age
            )
            improve_chance, stable_chance, decline_chance = cat_params["weights"]

            # Calculate ranges based on age category and attribute category
            if age_category == AgeCategory.YOUNG:
                # Apply curve modifier to base growth rate before distance multiplier
                modified_growth = growth_rate * curve_modifiers["growth"]
                effective_rate = modified_growth * distance_multiplier
                base_improve_range = self._rate_to_range(effective_rate, positive=True)
                # Blend with category-specific range
                improve_range = (
                    max(cat_params["improve_range"][0], base_improve_range[0]),
                    max(cat_params["improve_range"][1], base_improve_range[1])
                )
                decline_range = cat_params["decline_range"]

            elif age_category == AgeCategory.PRIME:
                # Prime uses category-specific ranges directly
                improve_range = cat_params["improve_range"]
                decline_range = cat_params["decline_range"]

            else:  # VETERAN
                # Apply curve modifier to base regression rate before distance multiplier
                modified_regression = regression_rate * curve_modifiers["decline"]
                effective_rate = modified_regression * distance_multiplier
                base_decline_range = self._rate_to_range(effective_rate, positive=False)
                improve_range = cat_params["improve_range"]
                # Blend with category-specific range (use more severe decline)
                decline_range = (
                    min(cat_params["decline_range"][0], base_decline_range[0]),
                    min(cat_params["decline_range"][1], base_decline_range[1])
                )

            # Roll for change type
            roll = random.random()

            if roll < improve_chance:
                # Improvement
                change = random.randint(*improve_range)
                # Diminishing returns near max
                if current_value >= self.DIMINISHING_RETURNS_THRESHOLD:
                    change = max(1, change // 2)
                # Cap at individual potential (Tollgate 3) or global ceiling
                ceiling = potential if potential is not None else self.RATING_CEILING
                change = min(change, ceiling - current_value)
                if change > 0:
                    changes[attr] = change

            elif roll < improve_chance + decline_chance:
                # Decline
                change = random.randint(*decline_range)
                # Floor protection
                change = max(change, self.RATING_FLOOR - current_value)
                if change < 0:
                    changes[attr] = change
            # else: stable (no change)

        return changes

    def _rate_to_range(self, rate: float, positive: bool) -> tuple:
        """
        Convert a float rate to integer range for random selection.

        Args:
            rate: Base rate (e.g., 2.5 points/year)
            positive: True for improvement, False for decline

        Returns:
            Tuple (min, max) for random.randint()
        """
        base = int(rate)
        # Add variance: base-1 to base+1, with minimum of 1
        min_val = max(1, base - 1)
        max_val = base + 1

        if positive:
            return (min_val, max_val)
        else:
            return (-max_val, -min_val)


class TrainingCampService:
    """
    Service for training camp stage operations.

    Manages:
    - Processing all league players for attribute adjustments
    - Age-weighted development algorithm
    - Persisting updated attributes to database
    - Generating depth charts based on new ratings
    - Generating before/after comparison data for UI
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        algorithm: Optional[DevelopmentAlgorithm] = None
    ):
        """
        Initialize the training camp service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
            algorithm: Optional custom development algorithm (default: AgeWeightedDevelopment)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._algorithm = algorithm or AgeWeightedDevelopment()
        self._logger = logging.getLogger(__name__)
        self._history_api = ProgressionHistoryAPI(db_path)

    def process_all_players(self) -> Dict[str, Any]:
        """
        Process training camp for ALL league players.

        Returns:
            Dict containing:
                - results: List[PlayerDevelopmentResult] for all players
                - summary: Dict with aggregated stats
                - by_team: Dict[int, List[PlayerDevelopmentResult]] grouped by team
                - depth_chart_summary: Dict with depth chart update info
        """
        all_results: List[PlayerDevelopmentResult] = []
        results_by_team: Dict[int, List[PlayerDevelopmentResult]] = {}

        # Get ALL players in the dynasty (all 32 teams + free agents)
        players = self._get_all_dynasty_players()

        self._logger.info(f"Processing training camp for {len(players)} players")

        for player in players:
            result = self._process_single_player(player)
            all_results.append(result)

            team_id = result.team_id
            if team_id not in results_by_team:
                results_by_team[team_id] = []
            results_by_team[team_id].append(result)

        # Persist all changes to database
        updated_count = self._persist_attribute_changes(all_results)

        # Regenerate depth charts for all 32 teams
        depth_chart_summary = self._regenerate_all_depth_charts()

        # Calculate summary statistics
        summary = self._calculate_summary(all_results)

        self._logger.info(
            f"Training camp complete: {updated_count} players updated, "
            f"{summary['improved_count']} improved, {summary['declined_count']} declined"
        )

        return {
            "results": all_results,
            "summary": summary,
            "by_team": results_by_team,
            "depth_chart_summary": depth_chart_summary,
        }

    def _get_all_dynasty_players(self) -> List[Dict[str, Any]]:
        """Get all players in the dynasty (all teams + free agents)."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = """
                SELECT
                    p.player_id, p.first_name, p.last_name, p.team_id,
                    p.positions, p.attributes, p.birthdate
                FROM players p
                WHERE p.dynasty_id = ?
            """
            cursor.execute(query, (self._dynasty_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def _process_single_player(self, player: Dict[str, Any]) -> PlayerDevelopmentResult:
        """Process training camp for a single player."""
        player_id = player.get("player_id")
        first_name = player.get("first_name", "")
        last_name = player.get("last_name", "")
        player_name = f"{first_name} {last_name}".strip()
        team_id = player.get("team_id", 0)

        # Parse positions
        positions = player.get("positions", [])
        if isinstance(positions, str):
            positions = json.loads(positions)
        position = positions[0] if positions else "unknown"

        # Parse attributes
        attributes = player.get("attributes", {})
        if isinstance(attributes, str):
            attributes = json.loads(attributes)

        # Calculate age
        age = self._calculate_age(player.get("birthdate"))

        # Get archetype_id if available (for position-specific peak ages)
        archetype_id = attributes.get('archetype_id') or player.get('archetype_id')

        # Get age category (position-specific)
        age_category = self._algorithm.get_age_category(age, position, archetype_id)

        # Extract potential from attributes (Tollgate 3: Individual Player Potential)
        player_potential = attributes.get('potential')
        if player_potential is None:
            # Default: overall + 5 if not set (for existing players without potential)
            player_potential = min(99, int(attributes.get('overall', 70)) + 5)

        # Calculate attribute changes with potential ceiling and development curve
        changes_dict = self._algorithm.calculate_changes(
            age, position, attributes,
            potential=player_potential,
            archetype_id=archetype_id
        )

        # Build attribute change records
        attribute_changes = []
        for attr_name, change_value in changes_dict.items():
            if change_value != 0:
                old_value = int(attributes.get(attr_name, 0))
                new_value = max(40, min(99, old_value + change_value))
                attribute_changes.append(AttributeChange(
                    attribute_name=attr_name,
                    old_value=old_value,
                    new_value=new_value,
                    change=new_value - old_value
                ))

        # Calculate new overall
        old_overall = int(attributes.get("overall", 70))
        new_overall = self._recalculate_overall(attributes, changes_dict, position)

        # Get development type from archetype (Tollgate 7: UI Integration)
        dev_type = "N"
        if archetype_id:
            curve = self._algorithm._get_archetype_development_curve(archetype_id)
            dev_type = {"early": "E", "normal": "N", "late": "L"}.get(curve, "N")

        return PlayerDevelopmentResult(
            player_id=player_id,
            player_name=player_name,
            position=position,
            age=age,
            team_id=team_id,
            age_category=age_category,
            old_overall=old_overall,
            new_overall=new_overall,
            overall_change=new_overall - old_overall,
            attribute_changes=attribute_changes,
            potential=player_potential,
            dev_type=dev_type,
        )

    def _calculate_age(self, birthdate: Optional[str]) -> int:
        """Calculate age from birthdate string (YYYY-MM-DD)."""
        if not birthdate:
            return 25  # Default age
        try:
            birth_year = int(birthdate.split("-")[0])
            return self._season - birth_year
        except (ValueError, IndexError):
            return 25

    def _recalculate_overall(
        self,
        current_attrs: Dict[str, Any],
        changes: Dict[str, int],
        position: str
    ) -> int:
        """
        Recalculate overall rating after attribute changes.

        Uses weighted average of position-relevant attributes.
        """
        # Apply changes to get new attribute values
        new_attrs = dict(current_attrs)
        for attr_name, change in changes.items():
            if attr_name in new_attrs:
                old_val = new_attrs[attr_name]
                if isinstance(old_val, (int, float)):
                    new_attrs[attr_name] = max(40, min(99, int(old_val) + change))

        # Get position-relevant attributes for overall calculation
        position_key = normalize_position(position)
        relevant = AgeWeightedDevelopment.POSITION_ATTRIBUTES.get(
            position_key, ['awareness']
        )

        # Calculate weighted average (awareness counts extra)
        total = 0.0
        count = 0.0
        for attr in relevant:
            if attr in new_attrs and isinstance(new_attrs[attr], (int, float)):
                weight = 1.5 if attr == 'awareness' else 1.0
                total += float(new_attrs[attr]) * weight
                count += weight

        if count > 0:
            return int(round(total / count))
        return int(current_attrs.get("overall", 70))

    def _persist_attribute_changes(
        self,
        results: List[PlayerDevelopmentResult]
    ) -> int:
        """
        Persist all attribute changes to the database.

        Returns:
            Number of players updated
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        updated_count = 0

        try:
            for result in results:
                if not result.attribute_changes and result.overall_change == 0:
                    continue  # No changes to persist

                # Get current attributes from DB
                query = "SELECT attributes FROM players WHERE dynasty_id = ? AND player_id = ?"
                cursor.execute(query, (self._dynasty_id, result.player_id))
                row = cursor.fetchone()

                if not row:
                    continue

                current_attrs = row['attributes']
                if isinstance(current_attrs, str):
                    current_attrs = json.loads(current_attrs)

                # Apply changes
                for change in result.attribute_changes:
                    current_attrs[change.attribute_name] = change.new_value

                # Update overall
                current_attrs["overall"] = result.new_overall

                # Persist to database
                update_query = """
                    UPDATE players
                    SET attributes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE dynasty_id = ? AND player_id = ?
                """
                cursor.execute(
                    update_query,
                    (json.dumps(current_attrs), self._dynasty_id, result.player_id)
                )
                updated_count += 1

            conn.commit()
            self._logger.info(f"Training camp: Updated {updated_count} players in database")

        except Exception as e:
            conn.rollback()
            self._logger.error(f"Error persisting training camp changes: {e}")
            raise
        finally:
            conn.close()

        # Persist progression history records via dedicated API
        history_records = []
        for result in results:
            if result.attribute_changes or result.overall_change != 0:
                history_records.append(ProgressionHistoryRecord(
                    player_id=result.player_id,
                    season=self._season,
                    age=result.age,
                    position=result.position,
                    team_id=result.team_id,
                    age_category=result.age_category.name,
                    overall_before=result.old_overall,
                    overall_after=result.new_overall,
                    overall_change=result.overall_change,
                    attribute_changes=[
                        {"attr": ac.attribute_name, "old": ac.old_value,
                         "new": ac.new_value, "change": ac.change}
                        for ac in result.attribute_changes
                    ]
                ))

        if history_records:
            try:
                inserted = self._history_api.insert_progression_records_batch(
                    self._dynasty_id, history_records
                )
                self._logger.info(f"Training camp: Inserted {inserted} progression history records")
            except Exception as e:
                self._logger.error(f"Error inserting progression history: {e}")
                # Don't re-raise - history is supplementary, player updates already committed

        return updated_count

    def _regenerate_all_depth_charts(self) -> Dict[str, Any]:
        """
        Regenerate depth charts for all 32 teams based on new ratings.

        Returns:
            Summary of depth chart updates
        """
        from depth_chart.depth_chart_api import DepthChartAPI

        depth_chart_api = DepthChartAPI(self._db_path)
        teams_updated = 0
        errors = []

        for team_id in range(1, 33):  # Teams 1-32
            try:
                success = depth_chart_api.auto_generate_depth_chart(
                    dynasty_id=self._dynasty_id,
                    team_id=team_id
                )
                if success:
                    teams_updated += 1
                else:
                    errors.append(f"Team {team_id}: auto_generate returned False")
            except Exception as e:
                self._logger.warning(f"Failed to regenerate depth chart for team {team_id}: {e}")
                errors.append(f"Team {team_id}: {str(e)}")

        self._logger.info(f"Depth charts regenerated for {teams_updated}/32 teams")

        return {
            "teams_updated": teams_updated,
            "total_teams": 32,
            "errors": errors if errors else None,
        }

    def _calculate_summary(
        self,
        results: List[PlayerDevelopmentResult]
    ) -> Dict[str, Any]:
        """Calculate summary statistics for training camp results."""
        total_players = len(results)
        improved = sum(1 for r in results if r.overall_change > 0)
        declined = sum(1 for r in results if r.overall_change < 0)
        unchanged = sum(1 for r in results if r.overall_change == 0)

        # Top gainers and biggest declines
        sorted_by_change = sorted(results, key=lambda r: r.overall_change, reverse=True)
        top_gainers = sorted_by_change[:10]
        biggest_declines = sorted_by_change[-10:][::-1]  # Reverse to show worst first

        # By age category
        by_age = {cat: [] for cat in AgeCategory}
        for r in results:
            by_age[r.age_category].append(r)

        return {
            "total_players": total_players,
            "improved_count": improved,
            "declined_count": declined,
            "unchanged_count": unchanged,
            "improved_pct": round(improved / total_players * 100, 1) if total_players else 0,
            "declined_pct": round(declined / total_players * 100, 1) if total_players else 0,
            "top_gainers": top_gainers,
            "biggest_declines": biggest_declines,
            "by_age_category": {
                cat.value: len(players) for cat, players in by_age.items()
            },
        }

    def get_player_progression_history(
        self,
        player_id: int,
        limit: int = 10
    ) -> List[dict]:
        """
        Get player's career progression history.

        Args:
            player_id: The player's ID
            limit: Maximum number of seasons to return (default 10)

        Returns:
            List of progression records, newest first
        """
        return self._history_api.get_player_history(
            self._dynasty_id, player_id, limit
        )