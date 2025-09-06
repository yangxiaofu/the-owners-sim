"""
Scoring Type Mapper

Provides clean conversion between FieldResult scoring_type strings 
and ScoringType enums. Maintains separation between field tracking
and scoreboard systems while enabling seamless integration.
"""

from typing import Optional
from .scoreboard import ScoringType


class ScoringTypeMapper:
    """
    Maps FieldResult scoring type strings to ScoringType enums
    
    Provides a clean interface for converting the string-based scoring_type 
    values from FieldResult into strongly-typed ScoringType enums for the 
    scoreboard system.
    
    This maintains separation of concerns:
    - FieldResult uses strings for simplicity and flexibility
    - Scoreboard uses enums for type safety and point value mapping
    """
    
    # Static mapping from field result strings to scoring types
    SCORING_MAP = {
        "touchdown": ScoringType.TOUCHDOWN,
        "field_goal": ScoringType.FIELD_GOAL,
        "safety": ScoringType.SAFETY,
        "extra_point": ScoringType.EXTRA_POINT,
        "two_point_conversion": ScoringType.TWO_POINT_CONVERSION,
        
        # Alternative spellings/formats for robustness
        "field goal": ScoringType.FIELD_GOAL,
        "fieldgoal": ScoringType.FIELD_GOAL,
        "fg": ScoringType.FIELD_GOAL,
        "td": ScoringType.TOUCHDOWN,
        "pat": ScoringType.EXTRA_POINT,
        "extra point": ScoringType.EXTRA_POINT,
        "2pt": ScoringType.TWO_POINT_CONVERSION,
        "two point": ScoringType.TWO_POINT_CONVERSION,
        "2 point": ScoringType.TWO_POINT_CONVERSION,
        "two_point": ScoringType.TWO_POINT_CONVERSION,
    }
    
    @classmethod
    def from_field_result(cls, scoring_type_str: str) -> Optional[ScoringType]:
        """
        Convert a FieldResult scoring_type string to ScoringType enum
        
        Args:
            scoring_type_str: String from FieldResult.scoring_type
            
        Returns:
            Corresponding ScoringType enum, or None if no mapping found
            
        Example:
            >>> ScoringTypeMapper.from_field_result("touchdown")
            ScoringType.TOUCHDOWN
            
            >>> ScoringTypeMapper.from_field_result("field_goal")
            ScoringType.FIELD_GOAL
        """
        if not scoring_type_str:
            return None
        
        # Normalize the string: lowercase, strip whitespace
        normalized = scoring_type_str.lower().strip()
        
        return cls.SCORING_MAP.get(normalized)
    
    @classmethod
    def is_valid_scoring_type(cls, scoring_type_str: str) -> bool:
        """
        Check if a string represents a valid scoring type
        
        Args:
            scoring_type_str: String to validate
            
        Returns:
            True if the string maps to a valid ScoringType
        """
        return cls.from_field_result(scoring_type_str) is not None
    
    @classmethod
    def get_points(cls, scoring_type_str: str) -> Optional[int]:
        """
        Get point value directly from scoring type string
        
        Args:
            scoring_type_str: String from FieldResult.scoring_type
            
        Returns:
            Point value for the scoring type, or None if invalid
        """
        scoring_type = cls.from_field_result(scoring_type_str)
        return scoring_type.value if scoring_type else None
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Get all supported scoring type strings
        
        Returns:
            List of all strings that can be mapped to ScoringType enums
        """
        return list(cls.SCORING_MAP.keys())
    
    @classmethod
    def get_canonical_types(cls) -> list[str]:
        """
        Get canonical (primary) scoring type strings
        
        Returns:
            List of primary scoring type strings (excludes alternatives)
        """
        return ["touchdown", "field_goal", "safety", "extra_point", "two_point_conversion"]