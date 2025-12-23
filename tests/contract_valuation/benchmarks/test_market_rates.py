"""
Unit tests for MarketRates class.

Tests market rate lookups, cap inflation, and NFL contracts JSON loading.
"""

import pytest

from contract_valuation.benchmarks.market_rates import (
    MarketRates,
    PositionMarketRate,
    load_nfl_contracts,
    get_contract_metadata,
)


@pytest.fixture
def rates():
    """MarketRates instance."""
    return MarketRates(season=2025)


class TestMarketRates:
    """Tests for MarketRates class."""

    def test_all_25_positions_have_rates(self, rates):
        """Verify all 25 positions return valid rates (directly or via mapping)."""
        # All 25 positions from CLAUDE.md
        all_positions = [
            "QB", "RB", "FB", "WR", "TE",
            "LT", "LG", "C", "RG", "RT",
            "LE", "DT", "RE",
            "LOLB", "MLB", "ROLB",
            "CB", "FS", "SS",
            "K", "P", "LS",
            "EDGE",
        ]

        for position in all_positions:
            rate = rates.get_rate(position, "starter")
            assert rate is not None, f"{position} should have a market rate"
            assert rate > 0, f"{position} rate should be positive"

    def test_elite_qb_rate_realistic(self, rates):
        """Verify elite QB rate is 45-55M range."""
        elite_qb_rate = rates.get_rate("QB", "elite")
        assert elite_qb_rate is not None
        assert 45_000_000 <= elite_qb_rate <= 55_000_000, (
            f"Elite QB rate should be 45-55M, got ${elite_qb_rate:,}"
        )

        # Quality QB should be 30-40M
        quality_qb_rate = rates.get_rate("QB", "quality")
        assert 30_000_000 <= quality_qb_rate <= 40_000_000

        # Starter QB should be 10-20M
        starter_qb_rate = rates.get_rate("QB", "starter")
        assert 10_000_000 <= starter_qb_rate <= 20_000_000

    def test_position_group_fallback(self, rates):
        """Verify LOLB returns EDGE rates."""
        # LOLB should map to EDGE
        lolb_rate = rates.get_rate("LOLB", "elite")
        edge_rate = rates.get_rate("EDGE", "elite")
        assert lolb_rate == edge_rate, "LOLB should use EDGE rates"

        # MLB should map to LB
        mlb_rate = rates.get_rate("MLB", "starter")
        lb_rate = rates.get_rate("LB", "starter")
        assert mlb_rate == lb_rate, "MLB should use LB rates"

        # FS should map to S
        fs_rate = rates.get_rate("FS", "quality")
        s_rate = rates.get_rate("S", "quality")
        assert fs_rate == s_rate, "FS should use S rates"

    def test_cap_inflation_adjustment(self, rates):
        """Test 2026 rate is ~8% higher than 2025."""
        base_rate_2025 = rates.get_rate("QB", "elite", season=2025)
        rate_2026 = rates.get_rate("QB", "elite", season=2026)

        # Should be approximately 8% higher
        expected_2026 = int(base_rate_2025 * 1.08)
        assert rate_2026 == expected_2026, (
            f"2026 rate should be 8% higher: expected ${expected_2026:,}, got ${rate_2026:,}"
        )

        # 2024 should be lower (negative inflation)
        rate_2024 = rates.get_rate("QB", "elite", season=2024)
        expected_2024 = int(base_rate_2025 / 1.08)
        assert rate_2024 == expected_2024

    def test_market_heat_range(self, rates):
        """Verify all heat values are 0.85-1.15."""
        # Check a variety of positions
        positions_to_check = ["QB", "RB", "WR", "CB", "EDGE", "LB", "S", "K", "P", "LS", "FB"]

        for position in positions_to_check:
            heat = rates.get_market_heat(position)
            assert 0.85 <= heat <= 1.15, (
                f"{position} market heat should be 0.85-1.15, got {heat}"
            )

        # Premium positions should have higher heat
        qb_heat = rates.get_market_heat("QB")
        rb_heat = rates.get_market_heat("RB")
        assert qb_heat > rb_heat, "QB should have higher market heat than RB"

    def test_tier_boundary_values(self, rates):
        """Test starter < quality < elite for all positions."""
        positions = ["QB", "WR", "RB", "CB", "EDGE", "TE", "DT", "LB", "S", "K", "P"]

        for position in positions:
            backup = rates.get_rate(position, "backup")
            starter = rates.get_rate(position, "starter")
            quality = rates.get_rate(position, "quality")
            elite = rates.get_rate(position, "elite")

            assert backup < starter < quality < elite, (
                f"{position} tiers should be ordered: backup < starter < quality < elite"
            )


class TestNFLContractsJSON:
    """Tests for nfl_contracts.json loading."""

    def test_nfl_contracts_json_loads(self):
        """Verify nfl_contracts.json loads without error."""
        contracts = load_nfl_contracts()

        assert isinstance(contracts, list)
        assert len(contracts) >= 40, f"Should have at least 40 contracts, got {len(contracts)}"

        # Check structure of first contract
        first = contracts[0]
        required_fields = [
            "player_name", "position", "team", "season_signed",
            "aav", "years", "total_value", "guaranteed", "guaranteed_pct",
            "tier", "age_at_signing"
        ]
        for field in required_fields:
            assert field in first, f"Contract should have {field} field"

    def test_contract_metadata_loads(self):
        """Verify contract metadata is accessible."""
        metadata = get_contract_metadata()

        assert "source" in metadata
        assert "last_updated" in metadata
        assert "cap_year" in metadata

    def test_contracts_have_valid_tiers(self):
        """Verify all contracts have valid tier values."""
        contracts = load_nfl_contracts()
        valid_tiers = {"backup", "starter", "quality", "elite"}

        for contract in contracts:
            tier = contract.get("tier")
            assert tier in valid_tiers, f"Invalid tier {tier} for {contract.get('player_name')}"

    def test_contracts_cover_key_positions(self):
        """Verify contracts cover premium positions."""
        contracts = load_nfl_contracts()
        positions = {c["position"] for c in contracts}

        key_positions = {"QB", "EDGE", "WR", "CB", "RB", "TE", "LB", "S", "K", "P"}
        for pos in key_positions:
            assert pos in positions, f"Should have contracts for {pos}"


class TestPositionMarketRate:
    """Tests for PositionMarketRate dataclass."""

    def test_position_market_rate_creation(self):
        """Test creating a PositionMarketRate."""
        rate = PositionMarketRate(
            position="QB",
            backup=3_000_000,
            starter=15_000_000,
            quality=35_000_000,
            elite=50_000_000,
            market_heat=1.10,
        )
        assert rate.position == "QB"
        assert rate.backup == 3_000_000
        assert rate.elite == 50_000_000
        assert rate.market_heat == 1.10

    def test_get_rate_method(self):
        """Test get_rate method returns correct tier."""
        rate = PositionMarketRate(
            position="WR",
            backup=2_000_000,
            starter=8_000_000,
            quality=18_000_000,
            elite=28_000_000,
        )
        assert rate.get_rate("backup") == 2_000_000
        assert rate.get_rate("starter") == 8_000_000
        assert rate.get_rate("quality") == 18_000_000
        assert rate.get_rate("elite") == 28_000_000
        assert rate.get_rate("invalid") == 8_000_000  # Defaults to starter


class TestTierForRating:
    """Tests for rating-to-tier mapping."""

    def test_tier_for_rating(self, rates):
        """Test rating-to-tier conversion."""
        assert rates.get_tier_for_rating(95) == "elite"
        assert rates.get_tier_for_rating(90) == "elite"
        assert rates.get_tier_for_rating(89) == "quality"
        assert rates.get_tier_for_rating(80) == "quality"
        assert rates.get_tier_for_rating(79) == "starter"
        assert rates.get_tier_for_rating(70) == "starter"
        assert rates.get_tier_for_rating(69) == "backup"
        assert rates.get_tier_for_rating(50) == "backup"
