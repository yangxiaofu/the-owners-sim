"""
Tests for position string normalization utility.

Validates that normalize_position() handles all edge cases:
- Lowercase conversion
- Space to underscore conversion
- Hyphen to underscore conversion
- Empty string handling
"""

import pytest
from src.constants.position_normalizer import normalize_position


class TestNormalizePosition:
    """Test suite for normalize_position() function."""

    # === Lowercase Conversion ===

    def test_lowercase_conversion_uppercase(self):
        """QUARTERBACK should become quarterback."""
        assert normalize_position("QUARTERBACK") == "quarterback"

    def test_lowercase_conversion_mixed_case(self):
        """Quarterback should become quarterback."""
        assert normalize_position("Quarterback") == "quarterback"

    def test_lowercase_already_lowercase(self):
        """Already lowercase should remain unchanged."""
        assert normalize_position("quarterback") == "quarterback"

    # === Space to Underscore ===

    def test_space_to_underscore(self):
        """'left tackle' should become 'left_tackle'."""
        assert normalize_position("left tackle") == "left_tackle"

    def test_space_to_underscore_mixed_case(self):
        """'Running Back' should become 'running_back'."""
        assert normalize_position("Running Back") == "running_back"

    def test_multiple_spaces(self):
        """Multiple spaces should all convert to underscores."""
        assert normalize_position("wide receiver extra") == "wide_receiver_extra"

    # === Hyphen to Underscore ===

    def test_hyphen_to_underscore(self):
        """'outside-linebacker' should become 'outside_linebacker'."""
        assert normalize_position("outside-linebacker") == "outside_linebacker"

    def test_hyphen_to_underscore_edge_rusher(self):
        """'edge-rusher' should become 'edge_rusher'."""
        assert normalize_position("edge-rusher") == "edge_rusher"

    def test_mixed_hyphen_and_space(self):
        """Mixed separators should all become underscores."""
        assert normalize_position("Left-Tackle") == "left_tackle"

    # === Combined Cases ===

    def test_uppercase_with_spaces(self):
        """'WIDE RECEIVER' should become 'wide_receiver'."""
        assert normalize_position("WIDE RECEIVER") == "wide_receiver"

    def test_mixed_case_with_hyphen(self):
        """'Strong-Safety' should become 'strong_safety'."""
        assert normalize_position("Strong-Safety") == "strong_safety"

    # === Already Normalized ===

    def test_already_normalized_underscore(self):
        """Already normalized should remain unchanged."""
        assert normalize_position("left_tackle") == "left_tackle"

    def test_already_normalized_single_word(self):
        """Single word lowercase should remain unchanged."""
        assert normalize_position("linebacker") == "linebacker"

    # === Abbreviations ===

    def test_abbreviation_uppercase(self):
        """'QB' should become 'qb'."""
        assert normalize_position("QB") == "qb"

    def test_abbreviation_lowercase(self):
        """'rb' should remain 'rb'."""
        assert normalize_position("rb") == "rb"

    def test_abbreviation_mixed(self):
        """'Qb' should become 'qb'."""
        assert normalize_position("Qb") == "qb"

    # === Edge Cases ===

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert normalize_position("") == ""

    def test_single_character(self):
        """Single character should be lowercased."""
        assert normalize_position("K") == "k"

    def test_only_spaces(self):
        """String of spaces should become underscores."""
        assert normalize_position("   ") == "___"

    def test_only_hyphens(self):
        """String of hyphens should become underscores."""
        assert normalize_position("---") == "___"


class TestPositionNormalizerIntegration:
    """Integration tests with real position names."""

    @pytest.mark.parametrize("input_pos,expected", [
        # Standard positions
        ("quarterback", "quarterback"),
        ("Quarterback", "quarterback"),
        ("QUARTERBACK", "quarterback"),
        ("QB", "qb"),
        # Running backs
        ("running_back", "running_back"),
        ("Running Back", "running_back"),
        ("RUNNING_BACK", "running_back"),
        ("RB", "rb"),
        # Offensive line
        ("left_tackle", "left_tackle"),
        ("Left Tackle", "left_tackle"),
        ("left-tackle", "left_tackle"),
        ("LT", "lt"),
        # Linebackers (problematic hyphen case)
        ("outside_linebacker", "outside_linebacker"),
        ("Outside Linebacker", "outside_linebacker"),
        ("outside-linebacker", "outside_linebacker"),
        ("OLB", "olb"),
        # Defensive backs
        ("cornerback", "cornerback"),
        ("strong_safety", "strong_safety"),
        ("Strong Safety", "strong_safety"),
        ("strong-safety", "strong_safety"),
        ("SS", "ss"),
        # Edge cases
        ("edge", "edge"),
        ("EDGE", "edge"),
        ("edge-rusher", "edge_rusher"),
    ])
    def test_real_positions(self, input_pos, expected):
        """Test all common position formats."""
        assert normalize_position(input_pos) == expected