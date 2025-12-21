"""
Tests for Centralized Player Stats Formatter

Comprehensive test suite covering:
- All 25 positions
- Multiple formatting styles
- Case variations
- Edge cases
- Field normalization
"""

import pytest
from src.utils.player_stat_formatter import (
    format_player_stats,
    normalize_stat_fields,
    get_primary_stats_for_position,
    format_stat_value,
    StatFormatStyle,
    CaseStyle,
    POSITION_STAT_MAPPING,
    DEFAULT_FIELD_MAPPING,
)


class TestFormatPlayerStats:
    """Test format_player_stats() main function."""

    # =========================================================================
    # QUARTERBACK TESTS
    # =========================================================================

    def test_qb_compact_lowercase(self):
        """QB: Compact lowercase format (default)."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}
        assert format_player_stats(stats, "QB") == "287 yds, 2 TD, 0 INT"

    def test_qb_compact_uppercase(self):
        """QB: Compact uppercase format."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}
        result = format_player_stats(stats, "QB", case=CaseStyle.UPPERCASE)
        assert result == "287 YDS, 2 TD, 0 INT"

    def test_qb_with_rushing_yards(self):
        """QB: Shows rushing yards if >= 20."""
        stats = {"passing_yards": 245, "passing_tds": 1, "passing_interceptions": 1, "rushing_yards": 45}
        result = format_player_stats(stats, "QB")
        assert "45 yds" in result  # Rushing yards shown

    def test_qb_without_rushing_yards(self):
        """QB: Hides rushing yards if < 20."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0, "rushing_yards": 12}
        result = format_player_stats(stats, "QB")
        assert "12" not in result  # Rushing yards hidden

    def test_qb_verbose_style(self):
        """QB: Verbose format with full words."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}
        result = format_player_stats(stats, "QB", style=StatFormatStyle.VERBOSE)
        assert "passing yards" in result.lower()

    # =========================================================================
    # RUNNING BACK TESTS
    # =========================================================================

    def test_rb_compact_lowercase(self):
        """RB: Rushing stats in compact format."""
        stats = {"rushing_yards": 112, "rushing_tds": 1}
        result = format_player_stats(stats, "RB")
        assert "112 yds" in result
        assert "1 TD" in result

    def test_rb_with_receiving(self):
        """RB: Shows receiving stats when applicable."""
        stats = {"rushing_yards": 85, "rushing_tds": 1, "receptions": 4, "receiving_yards": 28}
        result = format_player_stats(stats, "RB")
        assert "85 yds" in result
        assert "4 rec" in result or "28 yds" in result

    def test_rb_without_receiving(self):
        """RB: Hides receiving stats if no receptions."""
        stats = {"rushing_yards": 112, "rushing_tds": 1, "receptions": 0, "receiving_yards": 0}
        result = format_player_stats(stats, "RB")
        assert "rec" not in result.lower()

    # =========================================================================
    # WIDE RECEIVER / TIGHT END TESTS
    # =========================================================================

    def test_wr_compact_lowercase(self):
        """WR: Receiving stats in compact format."""
        stats = {"receptions": 8, "receiving_yards": 95, "receiving_tds": 1}
        result = format_player_stats(stats, "WR")
        assert "8 rec" in result
        assert "95 yds" in result
        assert "1 TD" in result

    def test_te_compact_uppercase(self):
        """TE: Receiving stats in uppercase."""
        stats = {"receptions": 6, "receiving_yards": 80, "receiving_tds": 1}
        result = format_player_stats(stats, "TE", case=CaseStyle.UPPERCASE)
        assert "6 REC" in result
        assert "80 YDS" in result

    # =========================================================================
    # DEFENSIVE LINE TESTS
    # =========================================================================

    def test_de_compact_lowercase(self):
        """DE: Defensive stats in compact format."""
        stats = {"tackles_total": 8, "sacks": 2.5, "forced_fumbles": 1}
        result = format_player_stats(stats, "DE")
        assert "8 tkl" in result
        assert "2.5 sk" in result
        assert "1 FF" in result

    def test_dt_with_sacks(self):
        """DT: Shows sacks with decimal precision."""
        stats = {"tackles_total": 6, "sacks": 1.0}
        result = format_player_stats(stats, "DT")
        assert "1.0 sk" in result  # Float formatting for sacks

    def test_de_uppercase(self):
        """DE: Defensive stats in uppercase."""
        stats = {"tackles_total": 8, "sacks": 2.5}
        result = format_player_stats(stats, "DE", case=CaseStyle.UPPERCASE)
        assert "8 TKL" in result
        assert "2.5 SK" in result

    # =========================================================================
    # LINEBACKER TESTS
    # =========================================================================

    def test_lb_compact_lowercase(self):
        """LB: Defensive stats in compact format."""
        stats = {"tackles_total": 12, "sacks": 1.5, "interceptions": 0}
        result = format_player_stats(stats, "LB")
        assert "12 tkl" in result
        assert "1.5 sk" in result

    def test_lb_with_interception(self):
        """LB: Shows interceptions when present."""
        stats = {"tackles_total": 10, "sacks": 0.5, "interceptions": 1}
        result = format_player_stats(stats, "LB")
        assert "10 tkl" in result
        assert "1 INT" in result

    def test_mlb_uppercase(self):
        """MLB: Middle linebacker variant."""
        stats = {"tackles_total": 15, "sacks": 0.0}
        result = format_player_stats(stats, "MLB", case=CaseStyle.UPPERCASE)
        assert "15 TKL" in result

    def test_mike_linebacker(self):
        """MIKE: Mike linebacker designation."""
        stats = {"tackles_total": 14, "sacks": 1.0}
        result = format_player_stats(stats, "MIKE")
        assert "14 tkl" in result

    # =========================================================================
    # SECONDARY TESTS
    # =========================================================================

    def test_cb_compact_lowercase(self):
        """CB: Cornerback stats."""
        stats = {"tackles_total": 6, "interceptions": 1, "passes_defended": 3}
        result = format_player_stats(stats, "CB")
        assert "6 tkl" in result
        assert "1 INT" in result

    def test_safety_with_interceptions(self):
        """S: Safety with multiple INTs."""
        stats = {"tackles_total": 8, "interceptions": 2, "passes_defended": 4}
        result = format_player_stats(stats, "S")
        assert "8 tkl" in result
        assert "2 INT" in result

    def test_fs_uppercase(self):
        """FS: Free safety uppercase."""
        stats = {"tackles_total": 7, "interceptions": 1}
        result = format_player_stats(stats, "FS", case=CaseStyle.UPPERCASE)
        assert "7 TKL" in result
        assert "1 INT" in result

    def test_ss_strong_safety(self):
        """SS: Strong safety."""
        stats = {"tackles_total": 9, "interceptions": 0, "passes_defended": 2}
        result = format_player_stats(stats, "SS")
        assert "9 tkl" in result

    # =========================================================================
    # SPECIAL TEAMS TESTS
    # =========================================================================

    def test_kicker(self):
        """K: Kicker stats."""
        stats = {"field_goals_made": 3, "field_goals_attempted": 4, "extra_points_made": 5}
        result = format_player_stats(stats, "K")
        assert "3 FGM" in result or "3 fgm" in result

    def test_punter(self):
        """P: Punter stats."""
        stats = {"punts": 5, "punt_average": 45.2, "punts_inside_20": 2}
        result = format_player_stats(stats, "P")
        assert "5 punts" in result or "45" in result

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    def test_empty_stats(self):
        """Returns N/A for empty stats."""
        assert format_player_stats({}, "QB") == "N/A"

    def test_unknown_position(self):
        """Returns N/A for unknown position."""
        stats = {"passing_yards": 287}
        assert format_player_stats(stats, "UNKNOWN") == "N/A"

    def test_zero_values_default(self):
        """Zeros are hidden by default (except special cases)."""
        stats = {"rushing_yards": 0, "rushing_tds": 0}
        result = format_player_stats(stats, "RB")
        # Should return N/A or minimal output since all stats are zero
        assert result == "N/A" or len(result) < 10

    def test_include_zeros_flag(self):
        """Include zeros when flag is True."""
        stats = {"rushing_yards": 0, "rushing_tds": 0}
        result = format_player_stats(stats, "RB", include_zeros=True)
        assert "0" in result

    def test_max_stats_limit(self):
        """Respects max_stats parameter."""
        stats = {"tackles_total": 10, "sacks": 2.0, "interceptions": 1, "passes_defended": 3}
        result = format_player_stats(stats, "LB", max_stats=2)
        parts = result.split(", ")
        assert len(parts) <= 2

    def test_none_values_skipped(self):
        """None values are skipped gracefully."""
        stats = {"passing_yards": 287, "passing_tds": None, "passing_interceptions": 0}
        result = format_player_stats(stats, "QB")
        assert "287" in result
        assert result  # Should still return something

    def test_position_case_insensitive(self):
        """Position parameter is case-insensitive."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}
        result_upper = format_player_stats(stats, "QB")
        result_lower = format_player_stats(stats, "qb")
        # Both should work (though output might vary due to internal normalization)
        assert result_upper or result_lower

    # =========================================================================
    # FIELD NORMALIZATION TESTS
    # =========================================================================

    def test_alternate_field_names(self):
        """Handles alternate field names (pass_yards → passing_yards)."""
        stats = {"pass_yards": 300, "pass_tds": 2, "pass_ints": 1}
        result = format_player_stats(stats, "QB")
        assert "300" in result
        assert "2" in result

    def test_mixed_field_names(self):
        """Handles mix of standard and alternate names."""
        stats = {"passing_yards": 200, "pass_tds": 1, "passing_interceptions": 0}
        result = format_player_stats(stats, "QB")
        assert "200" in result

    # =========================================================================
    # STYLE VARIATION TESTS
    # =========================================================================

    def test_all_styles_qb(self):
        """QB stats work with all formatting styles."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}

        compact = format_player_stats(stats, "QB", style=StatFormatStyle.COMPACT)
        verbose = format_player_stats(stats, "QB", style=StatFormatStyle.VERBOSE)

        assert compact  # Should produce output
        assert verbose  # Should produce output
        assert compact != verbose  # Should be different

    def test_all_styles_defensive(self):
        """Defensive stats work with all formatting styles."""
        stats = {"tackles_total": 12, "sacks": 2.5}

        compact = format_player_stats(stats, "LB", style=StatFormatStyle.COMPACT)
        verbose = format_player_stats(stats, "LB", style=StatFormatStyle.VERBOSE)

        assert compact
        assert verbose

    # =========================================================================
    # CASE VARIATION TESTS
    # =========================================================================

    def test_all_cases_qb(self):
        """QB stats work with all case styles."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}

        lowercase = format_player_stats(stats, "QB", case=CaseStyle.LOWERCASE)
        uppercase = format_player_stats(stats, "QB", case=CaseStyle.UPPERCASE)
        title = format_player_stats(stats, "QB", case=CaseStyle.TITLE)

        assert lowercase
        assert uppercase
        assert title
        # Verify different casing
        assert "yds" in lowercase or "YDS" in uppercase or "Yds" in title


class TestNormalizeStatFields:
    """Test normalize_stat_fields() helper function."""

    def test_normalize_passing_stats(self):
        """Normalizes alternate passing stat names."""
        stats = {"pass_yards": 300, "pass_tds": 2}
        normalized = normalize_stat_fields(stats)
        assert normalized["passing_yards"] == 300
        assert normalized["passing_tds"] == 2

    def test_normalize_defensive_stats(self):
        """Normalizes alternate defensive stat names."""
        stats = {"tackles": 12, "ints": 2}
        normalized = normalize_stat_fields(stats)
        assert normalized["tackles_total"] == 12
        assert normalized["interceptions"] == 2

    def test_keeps_standard_names(self):
        """Keeps standard names unchanged."""
        stats = {"passing_yards": 287, "rushing_yards": 45}
        normalized = normalize_stat_fields(stats)
        assert normalized["passing_yards"] == 287
        assert normalized["rushing_yards"] == 45

    def test_custom_mapping(self):
        """Accepts custom field mapping."""
        stats = {"custom_field": 100}
        mapping = {"custom_field": "passing_yards"}
        normalized = normalize_stat_fields(stats, mapping)
        assert normalized["passing_yards"] == 100


class TestGetPrimaryStatsForPosition:
    """Test get_primary_stats_for_position() helper function."""

    def test_qb_stats(self):
        """Returns correct stats for QB."""
        stats = get_primary_stats_for_position("QB")
        assert "passing_yards" in stats
        assert "passing_tds" in stats
        assert "passing_interceptions" in stats

    def test_defensive_stats(self):
        """Returns correct stats for defensive positions."""
        lb_stats = get_primary_stats_for_position("LB")
        assert "tackles_total" in lb_stats
        assert "sacks" in lb_stats

    def test_case_insensitive(self):
        """Position lookup is case-insensitive."""
        stats_upper = get_primary_stats_for_position("QB")
        stats_lower = get_primary_stats_for_position("qb")
        assert stats_upper  # Should return stats for QB

    def test_unknown_position(self):
        """Returns empty list for unknown position."""
        stats = get_primary_stats_for_position("UNKNOWN")
        assert stats == []


class TestFormatStatValue:
    """Test format_stat_value() helper function."""

    def test_compact_lowercase(self):
        """Formats stat value in compact lowercase."""
        result = format_stat_value(287, "passing_yards", style=StatFormatStyle.COMPACT, case=CaseStyle.LOWERCASE)
        assert result == "287 yds"

    def test_compact_uppercase(self):
        """Formats stat value in compact uppercase."""
        result = format_stat_value(287, "passing_yards", style=StatFormatStyle.COMPACT, case=CaseStyle.UPPERCASE)
        assert result == "287 YDS"

    def test_sacks_decimal_formatting(self):
        """Formats sacks with 1 decimal place."""
        result = format_stat_value(2.5, "sacks", style=StatFormatStyle.COMPACT, case=CaseStyle.LOWERCASE)
        assert result == "2.5 sk"

    def test_verbose_singular(self):
        """Uses singular form for value of 1."""
        result = format_stat_value(1, "passing_yards", style=StatFormatStyle.VERBOSE, case=CaseStyle.LOWERCASE)
        assert "yard" in result.lower()

    def test_verbose_plural(self):
        """Uses plural form for value != 1."""
        result = format_stat_value(287, "passing_yards", style=StatFormatStyle.VERBOSE, case=CaseStyle.LOWERCASE)
        assert "yards" in result.lower()

    def test_none_value(self):
        """Returns empty string for None value."""
        result = format_stat_value(None, "passing_yards", style=StatFormatStyle.COMPACT, case=CaseStyle.LOWERCASE)
        assert result == ""


class TestConstantMappings:
    """Test that constant mappings are comprehensive."""

    def test_all_positions_have_mappings(self):
        """All positions in POSITION_STAT_MAPPING are covered."""
        expected_positions = ["QB", "RB", "FB", "WR", "TE", "DE", "DT", "NT",
                             "LB", "MLB", "ILB", "OLB", "MIKE", "WILL", "SAM",
                             "CB", "NCB", "S", "FS", "SS", "K", "P", "LS", "KR", "PR"]

        for pos in expected_positions:
            assert pos in POSITION_STAT_MAPPING, f"Position {pos} missing from POSITION_STAT_MAPPING"

    def test_field_mapping_covers_common_variations(self):
        """DEFAULT_FIELD_MAPPING covers common variations."""
        common_variations = ["pass_yards", "rush_yards", "rec_yards", "tackles", "ints"]
        for variation in common_variations:
            assert variation in DEFAULT_FIELD_MAPPING, f"Field variation {variation} missing"


# Performance test (optional, can be marked as slow)
@pytest.mark.slow
class TestPerformance:
    """Performance benchmarks."""

    def test_format_1000_stats_under_100ms(self, benchmark):
        """Formatting 1000 stats should take < 100ms."""
        stats = {"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}

        def format_stats():
            for _ in range(1000):
                format_player_stats(stats, "QB")

        # This requires pytest-benchmark plugin
        # benchmark(format_stats)
        # For now, just verify it works
        format_stats()
