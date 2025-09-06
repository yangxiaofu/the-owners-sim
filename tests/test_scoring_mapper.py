"""
Test Suite for Scoring Type Mapper

Tests the conversion between FieldResult scoring_type strings
and ScoringType enums, including edge cases and validation.
"""

import pytest
from src.game_management.scoring_mapper import ScoringTypeMapper
from src.game_management.scoreboard import ScoringType


class TestScoringTypeMapper:
    """Test ScoringTypeMapper functionality"""
    
    def test_canonical_scoring_types(self):
        """Test mapping of canonical scoring type strings"""
        # Test primary scoring types
        assert ScoringTypeMapper.from_field_result("touchdown") == ScoringType.TOUCHDOWN
        assert ScoringTypeMapper.from_field_result("field_goal") == ScoringType.FIELD_GOAL
        assert ScoringTypeMapper.from_field_result("safety") == ScoringType.SAFETY
        assert ScoringTypeMapper.from_field_result("extra_point") == ScoringType.EXTRA_POINT
        assert ScoringTypeMapper.from_field_result("two_point_conversion") == ScoringType.TWO_POINT_CONVERSION
    
    def test_alternative_spelling_mapping(self):
        """Test mapping of alternative spellings and formats"""
        # Field goal alternatives
        assert ScoringTypeMapper.from_field_result("field goal") == ScoringType.FIELD_GOAL
        assert ScoringTypeMapper.from_field_result("fieldgoal") == ScoringType.FIELD_GOAL
        assert ScoringTypeMapper.from_field_result("fg") == ScoringType.FIELD_GOAL
        
        # Touchdown alternatives
        assert ScoringTypeMapper.from_field_result("td") == ScoringType.TOUCHDOWN
        
        # Extra point alternatives
        assert ScoringTypeMapper.from_field_result("pat") == ScoringType.EXTRA_POINT
        assert ScoringTypeMapper.from_field_result("extra point") == ScoringType.EXTRA_POINT
        
        # Two point conversion alternatives
        assert ScoringTypeMapper.from_field_result("2pt") == ScoringType.TWO_POINT_CONVERSION
        assert ScoringTypeMapper.from_field_result("two point") == ScoringType.TWO_POINT_CONVERSION
        assert ScoringTypeMapper.from_field_result("2 point") == ScoringType.TWO_POINT_CONVERSION
        assert ScoringTypeMapper.from_field_result("two_point") == ScoringType.TWO_POINT_CONVERSION
    
    def test_case_insensitive_mapping(self):
        """Test that mapping is case insensitive"""
        assert ScoringTypeMapper.from_field_result("TOUCHDOWN") == ScoringType.TOUCHDOWN
        assert ScoringTypeMapper.from_field_result("TouchDown") == ScoringType.TOUCHDOWN
        assert ScoringTypeMapper.from_field_result("FIELD_GOAL") == ScoringType.FIELD_GOAL
        assert ScoringTypeMapper.from_field_result("Field Goal") == ScoringType.FIELD_GOAL
        assert ScoringTypeMapper.from_field_result("SAFETY") == ScoringType.SAFETY
    
    def test_whitespace_handling(self):
        """Test that whitespace is properly handled"""
        assert ScoringTypeMapper.from_field_result("  touchdown  ") == ScoringType.TOUCHDOWN
        assert ScoringTypeMapper.from_field_result("\tfield_goal\n") == ScoringType.FIELD_GOAL
        assert ScoringTypeMapper.from_field_result(" safety ") == ScoringType.SAFETY
    
    def test_invalid_scoring_types(self):
        """Test handling of invalid scoring type strings"""
        assert ScoringTypeMapper.from_field_result("invalid") is None
        assert ScoringTypeMapper.from_field_result("fumble") is None
        assert ScoringTypeMapper.from_field_result("interception") is None
        assert ScoringTypeMapper.from_field_result("punt") is None
        assert ScoringTypeMapper.from_field_result("") is None
        assert ScoringTypeMapper.from_field_result("123") is None
    
    def test_none_and_empty_inputs(self):
        """Test handling of None and empty inputs"""
        assert ScoringTypeMapper.from_field_result(None) is None
        assert ScoringTypeMapper.from_field_result("") is None
        assert ScoringTypeMapper.from_field_result("   ") is None
    
    def test_is_valid_scoring_type(self):
        """Test scoring type validation"""
        # Valid types
        assert ScoringTypeMapper.is_valid_scoring_type("touchdown") is True
        assert ScoringTypeMapper.is_valid_scoring_type("field_goal") is True
        assert ScoringTypeMapper.is_valid_scoring_type("safety") is True
        assert ScoringTypeMapper.is_valid_scoring_type("fg") is True
        assert ScoringTypeMapper.is_valid_scoring_type("TD") is True
        
        # Invalid types
        assert ScoringTypeMapper.is_valid_scoring_type("invalid") is False
        assert ScoringTypeMapper.is_valid_scoring_type("fumble") is False
        assert ScoringTypeMapper.is_valid_scoring_type("") is False
        assert ScoringTypeMapper.is_valid_scoring_type(None) is False
    
    def test_get_points(self):
        """Test getting point values directly from strings"""
        assert ScoringTypeMapper.get_points("touchdown") == 6
        assert ScoringTypeMapper.get_points("field_goal") == 3
        assert ScoringTypeMapper.get_points("safety") == 2
        assert ScoringTypeMapper.get_points("extra_point") == 1
        assert ScoringTypeMapper.get_points("two_point_conversion") == 2
        
        # Test alternatives
        assert ScoringTypeMapper.get_points("fg") == 3
        assert ScoringTypeMapper.get_points("td") == 6
        assert ScoringTypeMapper.get_points("pat") == 1
        
        # Test invalid
        assert ScoringTypeMapper.get_points("invalid") is None
        assert ScoringTypeMapper.get_points("") is None
    
    def test_get_supported_types(self):
        """Test getting list of supported scoring types"""
        supported = ScoringTypeMapper.get_supported_types()
        
        # Check that all canonical types are included
        assert "touchdown" in supported
        assert "field_goal" in supported
        assert "safety" in supported
        assert "extra_point" in supported
        assert "two_point_conversion" in supported
        
        # Check that alternatives are included
        assert "fg" in supported
        assert "td" in supported
        assert "pat" in supported
        
        # Should be a decent number of options
        assert len(supported) >= 10
    
    def test_get_canonical_types(self):
        """Test getting canonical (primary) scoring types"""
        canonical = ScoringTypeMapper.get_canonical_types()
        
        expected = ["touchdown", "field_goal", "safety", "extra_point", "two_point_conversion"]
        assert canonical == expected
        
        # Should not include alternatives
        assert "fg" not in canonical
        assert "td" not in canonical
        assert "pat" not in canonical
    
    def test_comprehensive_mapping_coverage(self):
        """Test that all canonical types have correct mappings"""
        canonical_types = ScoringTypeMapper.get_canonical_types()
        
        for scoring_type_str in canonical_types:
            # Should map to a valid ScoringType
            scoring_type = ScoringTypeMapper.from_field_result(scoring_type_str)
            assert scoring_type is not None
            assert isinstance(scoring_type, ScoringType)
            
            # Should be valid
            assert ScoringTypeMapper.is_valid_scoring_type(scoring_type_str)
            
            # Should have valid points
            points = ScoringTypeMapper.get_points(scoring_type_str)
            assert points is not None
            assert points > 0
            assert points == scoring_type.value
    
    def test_field_result_integration_simulation(self):
        """Test simulated integration with FieldResult scoring_type values"""
        # Simulate what we might get from FieldResult.scoring_type
        field_result_values = [
            "touchdown",      # Standard touchdown
            "field_goal",     # Standard field goal
            "safety",         # Safety
            None,             # No scoring
            "",               # Empty string
        ]
        
        expected_results = [
            ScoringType.TOUCHDOWN,
            ScoringType.FIELD_GOAL,
            ScoringType.SAFETY,
            None,
            None
        ]
        
        for field_value, expected in zip(field_result_values, expected_results):
            result = ScoringTypeMapper.from_field_result(field_value)
            assert result == expected
    
    def test_points_consistency(self):
        """Test that points from mapper match ScoringType enum values"""
        test_cases = [
            ("touchdown", ScoringType.TOUCHDOWN),
            ("field_goal", ScoringType.FIELD_GOAL),
            ("safety", ScoringType.SAFETY),
            ("extra_point", ScoringType.EXTRA_POINT),
            ("two_point_conversion", ScoringType.TWO_POINT_CONVERSION),
        ]
        
        for string_value, enum_value in test_cases:
            mapper_points = ScoringTypeMapper.get_points(string_value)
            enum_points = enum_value.value
            assert mapper_points == enum_points, f"Points mismatch for {string_value}: {mapper_points} != {enum_points}"