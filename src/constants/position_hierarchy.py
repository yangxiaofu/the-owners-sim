"""
Position Hierarchy System for The Owner's Sim

Defines parent-child position relationships to support flexible position matching.
Examples:
- left_guard IS-A guard IS-A offensive_line
- mike_linebacker IS-A linebacker IS-A defense
- free_safety IS-A safety IS-A defensive_back IS-A defense

This allows depth chart queries to find all guards when searching for left_guard,
and allows position searches to find specialized positions when searching generically.
"""

from typing import Dict, List, Optional, Set


class PositionHierarchy:
    """
    Position hierarchy system with parent-child relationships.

    Provides methods to check inheritance, get children, and traverse ancestors.
    """

    # Parent-child position mappings (child -> parent)
    # Format: specific_position -> generic_position
    HIERARCHY: Dict[str, str] = {
        # Offensive Line
        "left_tackle": "tackle",
        "right_tackle": "tackle",
        "tackle": "offensive_line",

        "left_guard": "guard",
        "right_guard": "guard",
        "guard": "offensive_line",

        "center": "offensive_line",
        "offensive_line": "offense",

        # Skill Positions
        "quarterback": "offense",
        "running_back": "offense",
        "fullback": "offense",
        "wide_receiver": "offense",
        "tight_end": "offense",

        # Defensive Line
        "defensive_end": "defensive_line",
        "defensive_tackle": "defensive_line",
        "nose_tackle": "defensive_line",
        "defensive_line": "defense",

        # Linebackers
        "mike_linebacker": "linebacker",
        "will_linebacker": "linebacker",
        "sam_linebacker": "linebacker",
        "outside_linebacker": "linebacker",
        "inside_linebacker": "linebacker",
        "linebacker": "defense",

        # Secondary
        "cornerback": "defensive_back",
        "free_safety": "safety",
        "strong_safety": "safety",
        "safety": "defensive_back",
        "defensive_back": "defense",

        # Special Teams
        "kicker": "special_teams",
        "punter": "special_teams",
        "long_snapper": "special_teams",
        "kick_returner": "special_teams",
        "punt_returner": "special_teams",
    }

    @classmethod
    def is_a(cls, position: str, parent_type: str) -> bool:
        """
        Check if a position inherits from a parent type.

        Args:
            position: Position to check (e.g., "left_guard")
            parent_type: Parent type to check against (e.g., "guard", "offensive_line")

        Returns:
            True if position IS-A parent_type, False otherwise

        Examples:
            >>> PositionHierarchy.is_a("left_guard", "guard")
            True
            >>> PositionHierarchy.is_a("left_guard", "offensive_line")
            True
            >>> PositionHierarchy.is_a("left_guard", "linebacker")
            False
        """
        if position == parent_type:
            return True

        current = position
        visited: Set[str] = set()

        while current in cls.HIERARCHY:
            if current in visited:
                # Circular reference protection
                break
            visited.add(current)

            current = cls.HIERARCHY[current]
            if current == parent_type:
                return True

        return False

    @classmethod
    def get_children(cls, parent_type: str) -> List[str]:
        """
        Get all child positions of a parent type.

        Args:
            parent_type: Parent type to get children for (e.g., "guard", "linebacker")

        Returns:
            List of all child positions (direct and indirect)

        Examples:
            >>> PositionHierarchy.get_children("guard")
            ["left_guard", "right_guard"]
            >>> PositionHierarchy.get_children("offensive_line")
            ["left_tackle", "right_tackle", "tackle", "left_guard", "right_guard", "guard", "center"]
        """
        children = []

        for position, parent in cls.HIERARCHY.items():
            if cls.is_a(position, parent_type) and position != parent_type:
                children.append(position)

        return children

    @classmethod
    def get_parent(cls, position: str) -> Optional[str]:
        """
        Get the immediate parent of a position.

        Args:
            position: Position to get parent for

        Returns:
            Parent position or None if no parent exists

        Examples:
            >>> PositionHierarchy.get_parent("left_guard")
            "guard"
            >>> PositionHierarchy.get_parent("guard")
            "offensive_line"
        """
        return cls.HIERARCHY.get(position)

    @classmethod
    def get_ancestors(cls, position: str) -> List[str]:
        """
        Get all ancestor positions of a position.

        Args:
            position: Position to get ancestors for

        Returns:
            List of all ancestor positions (from immediate parent to root)

        Examples:
            >>> PositionHierarchy.get_ancestors("left_guard")
            ["guard", "offensive_line", "offense"]
            >>> PositionHierarchy.get_ancestors("mike_linebacker")
            ["linebacker", "defense"]
        """
        ancestors = []
        current = position
        visited: Set[str] = set()

        while current in cls.HIERARCHY:
            if current in visited:
                # Circular reference protection
                break
            visited.add(current)

            parent = cls.HIERARCHY[current]
            ancestors.append(parent)
            current = parent

        return ancestors

    @classmethod
    def get_all_matching_positions(cls, position: str) -> List[str]:
        """
        Get all positions that match a position query (self + all children).

        This is useful for depth chart queries where you want to find all
        guards (including left_guard and right_guard) when searching for "guard".

        Args:
            position: Position to match

        Returns:
            List of all matching positions (self + all descendants)

        Examples:
            >>> PositionHierarchy.get_all_matching_positions("guard")
            ["guard", "left_guard", "right_guard"]
            >>> PositionHierarchy.get_all_matching_positions("left_guard")
            ["left_guard"]
        """
        matching = [position]  # Include the position itself
        matching.extend(cls.get_children(position))
        return matching

    @classmethod
    def normalize_position(cls, position: str, target_specificity: str) -> str:
        """
        Normalize a position to a target specificity level.

        This is useful for converting specific positions to generic positions
        or vice versa.

        Args:
            position: Position to normalize
            target_specificity: Target level (e.g., "guard", "offensive_line")

        Returns:
            Normalized position if it matches hierarchy, original position otherwise

        Examples:
            >>> PositionHierarchy.normalize_position("left_guard", "guard")
            "guard"
            >>> PositionHierarchy.normalize_position("tackle", "offensive_line")
            "offensive_line"
        """
        if cls.is_a(position, target_specificity):
            return target_specificity
        return position
