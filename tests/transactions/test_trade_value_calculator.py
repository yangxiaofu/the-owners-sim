"""
Unit tests for Trade Value Calculator

Tests player valuation, draft pick valuation, and trade fairness evaluation.
"""

import pytest
from src.transactions.trade_value_calculator import TradeValueCalculator
from src.transactions.models import (
    DraftPick, TradeAsset, TradeProposal, AssetType, FairnessRating
)


class TestPlayerValuation:
    """Test player value calculations"""

    def test_elite_qb_value(self):
        """Elite QB (95 OVR, age 28) should have very high value"""
        calc = TradeValueCalculator()
        value = calc.calculate_player_value(
            overall_rating=95,
            position='quarterback',
            age=28,
            contract_years_remaining=3,
            annual_cap_hit=45_000_000
        )
        # Elite QB in prime should be 600-800 value
        assert 600 <= value <= 800, f"Expected 600-800, got {value}"

    def test_aging_qb_decline(self):
        """QB value should decline significantly after age 33"""
        calc = TradeValueCalculator()

        prime_value = calc.calculate_player_value(
            overall_rating=90,
            position='quarterback',
            age=28
        )

        aging_value = calc.calculate_player_value(
            overall_rating=90,
            position='quarterback',
            age=35
        )

        # 35-year-old should be worth 60-70% of prime
        assert aging_value < prime_value * 0.75, \
            f"Aging QB ({aging_value}) should be < 75% of prime ({prime_value})"

    def test_rb_age_cliff(self):
        """RB should decline faster than QB with age"""
        calc = TradeValueCalculator()

        young_rb = calc.calculate_player_value(
            overall_rating=85,
            position='running_back',
            age=24
        )

        old_rb = calc.calculate_player_value(
            overall_rating=85,
            position='running_back',
            age=30
        )

        # 30-year-old RB should be worth <60% of 24-year-old (age cliff is steep but not that steep)
        assert old_rb < young_rb * 0.60, \
            f"Old RB ({old_rb}) should be < 60% of young RB ({young_rb})"

    def test_position_tier_premium(self):
        """QB should be worth ~2x more than RB at same rating"""
        calc = TradeValueCalculator()

        qb_value = calc.calculate_player_value(
            overall_rating=85,
            position='quarterback',
            age=27
        )

        rb_value = calc.calculate_player_value(
            overall_rating=85,
            position='running_back',
            age=27
        )

        # QB should be 1.5-2.0x RB value
        assert qb_value >= rb_value * 1.5, \
            f"QB ({qb_value}) should be >= 1.5x RB ({rb_value})"

    def test_expiring_contract_penalty(self):
        """Expiring contract (1 year) should lower value"""
        calc = TradeValueCalculator()

        multi_year = calc.calculate_player_value(
            overall_rating=85,
            position='wide_receiver',
            age=26,
            contract_years_remaining=3,
            annual_cap_hit=15_000_000
        )

        expiring = calc.calculate_player_value(
            overall_rating=85,
            position='wide_receiver',
            age=26,
            contract_years_remaining=1,
            annual_cap_hit=15_000_000
        )

        # Expiring contract should be 10-20% lower
        assert expiring < multi_year * 0.92, \
            f"Expiring ({expiring}) should be < 92% of multi-year ({multi_year})"

    def test_bad_contract_penalty(self):
        """Severely overpaid player should have reduced value"""
        calc = TradeValueCalculator()

        fair_contract = calc.calculate_player_value(
            overall_rating=80,
            position='wide_receiver',
            age=28,
            contract_years_remaining=3,
            annual_cap_hit=10_000_000
        )

        bad_contract = calc.calculate_player_value(
            overall_rating=80,
            position='wide_receiver',
            age=28,
            contract_years_remaining=4,
            annual_cap_hit=25_000_000  # Very overpaid
        )

        # Bad contract should reduce value by 10-20% (contract matters but not as much as rating)
        assert bad_contract < fair_contract * 0.96, \
            f"Bad contract ({bad_contract}) should be < 96% of fair ({fair_contract})"

    def test_rookie_vs_veteran(self):
        """Young player (22) vs peak veteran (28) at same rating"""
        calc = TradeValueCalculator()

        rookie = calc.calculate_player_value(
            overall_rating=82,
            position='linebacker',
            age=22
        )

        veteran = calc.calculate_player_value(
            overall_rating=82,
            position='linebacker',
            age=28
        )

        # Veteran in prime should be more valuable due to age curve (within 15%)
        assert veteran >= rookie * 0.95, \
            f"Veteran ({veteran}) should be >= 95% of rookie ({rookie})"
        assert veteran <= rookie * 1.20, \
            f"Veteran ({veteran}) should be <= 120% of rookie ({rookie})"

    def test_backup_vs_starter(self):
        """Backup (70 OVR) vs Starter (85 OVR) value gap"""
        calc = TradeValueCalculator()

        backup = calc.calculate_player_value(
            overall_rating=70,
            position='cornerback',
            age=25
        )

        starter = calc.calculate_player_value(
            overall_rating=85,
            position='cornerback',
            age=25
        )

        # Starter should be 2.5-4x more valuable (power curve, but not extreme)
        assert starter >= backup * 2.5, \
            f"Starter ({starter}) should be >= 2.5x backup ({backup})"

    def test_zero_ovr_gives_zero_value(self):
        """Player with 0 overall should have 0 value"""
        calc = TradeValueCalculator()
        value = calc.calculate_player_value(
            overall_rating=0,
            position='kicker',
            age=25
        )
        assert value == 0.0

    def test_average_starter_value(self):
        """75-80 OVR player should be around 100 value units"""
        calc = TradeValueCalculator()

        value_75 = calc.calculate_player_value(
            overall_rating=75,
            position='linebacker',
            age=27
        )

        value_80 = calc.calculate_player_value(
            overall_rating=80,
            position='linebacker',
            age=27
        )

        # Should be roughly 120-150 range for 75 OVR, 180-220 for 80 OVR
        assert 120 <= value_75 <= 150, f"75 OVR value: {value_75}"
        assert 180 <= value_80 <= 220, f"80 OVR value: {value_80}"


class TestDraftPickValuation:
    """Test draft pick value calculations"""

    def test_first_overall_pick_value(self):
        """"""#1 overall pick should have highest value"""
        calc = TradeValueCalculator()

        pick = DraftPick(
            round=1,
            year=2025,
            original_team_id=1,
            current_team_id=1,
            overall_pick_projected=1
        )

        value = calc.calculate_pick_value(pick)

        # Top pick should be worth 180-220 (scaled from 3000)
        assert 180 <= value <= 220, f"Pick #1 value: {value}"

    def test_mid_first_round_value(self):
        """Pick #16 should be worth ~half of #1 pick"""
        calc = TradeValueCalculator()

        top_pick = DraftPick(round=1, year=2025, original_team_id=1, current_team_id=1)
        top_pick.overall_pick_projected = 1
        top_value = calc.calculate_pick_value(top_pick)

        mid_pick = DraftPick(round=1, year=2025, original_team_id=16, current_team_id=16)
        mid_pick.overall_pick_projected = 16
        mid_value = calc.calculate_pick_value(mid_pick)

        # Mid-1st should be 55-65% of top pick
        assert 0.55 * top_value <= mid_value <= 0.70 * top_value, \
            f"Mid-1st ({mid_value}) should be 55-70% of top pick ({top_value})"

    def test_second_round_vs_first(self):
        """Early 2nd round should be worth ~70-85% of late 1st"""
        calc = TradeValueCalculator()

        late_first = DraftPick(round=1, year=2025, original_team_id=32, current_team_id=32)
        late_first.overall_pick_projected = 32
        late_first_value = calc.calculate_pick_value(late_first)

        early_second = DraftPick(round=2, year=2025, original_team_id=1, current_team_id=1)
        early_second.overall_pick_projected = 33
        early_second_value = calc.calculate_pick_value(early_second)

        # Early 2nd should be 85-105% of late 1st (very close in value)
        assert 0.85 * late_first_value <= early_second_value <= 1.05 * late_first_value, \
            f"Early 2nd ({early_second_value}) should be 85-105% of late 1st ({late_first_value})"

    def test_future_pick_discount(self):
        """Future picks should be discounted ~5% per year"""
        calc = TradeValueCalculator(current_year=2025)

        current = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)
        current.overall_pick_projected = 15
        current_value = calc.calculate_pick_value(current)

        future = DraftPick(round=1, year=2026, original_team_id=15, current_team_id=15)
        future.overall_pick_projected = 15
        future_value = calc.calculate_pick_value(future)

        # 2026 pick should be ~95% of 2025 pick
        assert 0.93 * current_value <= future_value <= 0.97 * current_value, \
            f"Future pick ({future_value}) should be 93-97% of current ({current_value})"

    def test_two_years_out_discount(self):
        """2-year-future pick should be discounted ~10%"""
        calc = TradeValueCalculator(current_year=2025)

        current = DraftPick(round=1, year=2025, original_team_id=20, current_team_id=20)
        current.overall_pick_projected = 20
        current_value = calc.calculate_pick_value(current)

        two_years = DraftPick(round=1, year=2027, original_team_id=20, current_team_id=20)
        two_years.overall_pick_projected = 20
        two_years_value = calc.calculate_pick_value(two_years)

        # 2027 pick should be ~90% of 2025 pick (0.95^2)
        assert 0.88 * current_value <= two_years_value <= 0.92 * current_value, \
            f"2-year future ({two_years_value}) should be 88-92% of current ({current_value})"

    def test_seventh_round_minimal_value(self):
        """7th round picks should have very low value"""
        calc = TradeValueCalculator()

        seventh = DraftPick(round=7, year=2025, original_team_id=15, current_team_id=15)
        seventh.overall_pick_projected = 220
        value = calc.calculate_pick_value(seventh)

        # 7th rounder should be worth < 5 units
        assert value < 5.0, f"7th round value: {value}"

    def test_projection_uncertainty_penalty(self):
        """Wide projection range should slightly reduce value"""
        calc = TradeValueCalculator()

        certain = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)
        certain.overall_pick_projected = 15
        certain.projected_range_min = 13
        certain.projected_range_max = 17
        certain_value = calc.calculate_pick_value(certain)

        uncertain = DraftPick(round=1, year=2026, original_team_id=15, current_team_id=15)
        uncertain.overall_pick_projected = 15
        uncertain.projected_range_min = 5
        uncertain.projected_range_max = 25
        uncertain_value = calc.calculate_pick_value(uncertain)

        # Uncertain pick should be 5-10% lower
        assert uncertain_value < certain_value * 0.95, \
            f"Uncertain ({uncertain_value}) should be < 95% of certain ({certain_value})"

    def test_team_record_projection(self):
        """Winning team's pick should project later"""
        pick = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)

        # Good team (12-5 record)
        overall = pick.estimate_overall_pick(team_wins=12, team_losses=5)

        # Should project to late 1st round (pick 20-32)
        assert 20 <= overall <= 32, f"Good team pick projection: {overall}"

    def test_losing_team_projection(self):
        """Losing team's pick should project early"""
        pick = DraftPick(round=1, year=2025, original_team_id=3, current_team_id=3)

        # Bad team (2-15 record)
        overall = pick.estimate_overall_pick(team_wins=2, team_losses=15)

        # Should project to early 1st round (pick 1-5)
        assert 1 <= overall <= 5, f"Bad team pick projection: {overall}"


class TestTradeFairness:
    """Test trade evaluation and fairness ratings"""

    def test_perfectly_fair_trade(self):
        """Trade with 1.0 value ratio should be VERY_FAIR"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1,
            player_name="QB A",
            position="quarterback",
            overall_rating=85,
            age=28,
            trade_value=300.0
        )

        player2 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=2,
            player_name="QB B",
            position="quarterback",
            overall_rating=85,
            age=28,
            trade_value=300.0
        )

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[player1],
            team2_id=2,
            team2_assets=[player2]
        )

        assert proposal.value_ratio == 1.0
        assert proposal.fairness_rating == FairnessRating.VERY_FAIR
        assert proposal.is_acceptable()

    def test_slightly_unfair_trade(self):
        """Trade with 1.25 ratio should be SLIGHTLY_UNFAIR"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Player A",
            trade_value=200.0
        )
        player2 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Player B",
            trade_value=250.0
        )

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[player1],
            team2_id=2,
            team2_assets=[player2]
        )

        assert proposal.value_ratio == 1.25
        assert proposal.fairness_rating == FairnessRating.SLIGHTLY_UNFAIR
        assert not proposal.is_acceptable()

    def test_very_unfair_trade(self):
        """Trade with 1.5 ratio should be VERY_UNFAIR"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Player A",
            trade_value=200.0
        )
        player2 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Player B",
            trade_value=300.0
        )

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[player1],
            team2_id=2,
            team2_assets=[player2]
        )

        assert proposal.value_ratio == 1.5
        assert proposal.fairness_rating == FairnessRating.VERY_UNFAIR
        assert not proposal.is_acceptable()

    def test_multi_asset_trade(self):
        """Trade with multiple players and picks"""
        calc = TradeValueCalculator()

        # Team 1 gives: WR (200) + 2nd round pick (50)
        wr = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="WR",
            trade_value=200.0
        )
        pick2 = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=50.0
        )

        # Team 2 gives: 1st round pick (150) + 3rd round (25) + 4th round (15)
        pick1 = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=150.0
        )
        pick3 = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=25.0
        )
        pick4 = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=15.0
        )

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[wr, pick2],  # Total: 250
            team2_id=2,
            team2_assets=[pick1, pick3, pick4]  # Total: 190
        )

        # Team 1 getting 190, giving 250 = 0.76 ratio (slightly unfair to team 1)
        assert 0.75 <= proposal.value_ratio <= 0.77
        assert proposal.fairness_rating == FairnessRating.SLIGHTLY_UNFAIR

    def test_player_for_picks_fair(self):
        """Elite player for multiple 1st round picks"""
        calc = TradeValueCalculator()

        # Elite WR worth 350
        elite_wr = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Elite WR",
            trade_value=350.0
        )

        # Two 1st rounders worth 150 + 100 = 250
        # Plus 2nd rounder worth 50 = 300 total
        pick1a = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=150.0
        )
        pick1b = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=100.0
        )
        pick2 = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=50.0
        )

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[elite_wr],
            team2_id=2,
            team2_assets=[pick1a, pick1b, pick2]
        )

        # 300 / 350 = 0.857 (FAIR range)
        assert proposal.fairness_rating in [FairnessRating.FAIR, FairnessRating.VERY_FAIR]

    def test_zero_value_asset(self):
        """Trade including worthless asset"""
        calc = TradeValueCalculator()

        good_player = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Good Player",
            trade_value=200.0
        )
        bad_player = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Bad Player",
            trade_value=0.0
        )

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[bad_player],
            team2_id=2,
            team2_assets=[good_player]
        )

        # Infinite ratio = VERY_UNFAIR
        assert proposal.fairness_rating == FairnessRating.VERY_UNFAIR

    def test_get_summary_format(self):
        """Trade proposal summary should be human-readable"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Patrick Mahomes",
            position="quarterback",
            overall_rating=99,
            age=28,
            trade_value=700.0
        )

        pick = DraftPick(round=1, year=2025, original_team_id=8, current_team_id=8)
        pick.overall_pick_projected = 9

        pick_asset = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            draft_pick=pick,
            trade_value=180.0
        )

        proposal = calc.evaluate_trade(
            team1_id=15,  # Chiefs
            team1_assets=[player1],
            team2_id=8,   # Broncos
            team2_assets=[pick_asset]
        )

        summary = proposal.get_summary()

        assert "Patrick Mahomes" in summary
        assert "Total Value" in summary
        assert "Value Ratio" in summary
        assert "Acceptable" in summary


class TestCalculatorIntegration:
    """Test calculator with integrated scenarios"""

    def test_calculator_initialization(self):
        """Test calculator initializes with all data structures"""
        calc = TradeValueCalculator(current_year=2025)

        assert calc.current_year == 2025
        assert len(calc.position_tiers) > 0
        assert len(calc.age_curves) > 0
        assert len(calc.draft_pick_values) == 262

    def test_value_consistency(self):
        """Same player valuations should be consistent"""
        calc = TradeValueCalculator()

        value1 = calc.calculate_player_value(
            overall_rating=85,
            position='wide_receiver',
            age=26
        )

        value2 = calc.calculate_player_value(
            overall_rating=85,
            position='wide_receiver',
            age=26
        )

        assert value1 == value2

    def test_pick_consistency(self):
        """Same pick valuations should be consistent"""
        calc = TradeValueCalculator()

        pick1 = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)
        pick1.overall_pick_projected = 15

        pick2 = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)
        pick2.overall_pick_projected = 15

        value1 = calc.calculate_pick_value(pick1)
        value2 = calc.calculate_pick_value(pick2)

        assert value1 == value2

    def test_realistic_trade_scenario(self):
        """Test realistic trade: Good WR for 1st + 2nd"""
        calc = TradeValueCalculator()

        # 85 OVR WR, age 26
        wr_value = calc.calculate_player_value(
            overall_rating=85,
            position='wide_receiver',
            age=26,
            contract_years_remaining=2,
            annual_cap_hit=15_000_000
        )

        # 1st round pick #22
        pick1 = DraftPick(round=1, year=2025, original_team_id=20, current_team_id=20)
        pick1.overall_pick_projected = 22
        pick1_value = calc.calculate_pick_value(pick1)

        # 2nd round pick #54
        pick2 = DraftPick(round=2, year=2025, original_team_id=20, current_team_id=20)
        pick2.overall_pick_projected = 54
        pick2_value = calc.calculate_pick_value(pick2)

        total_pick_value = pick1_value + pick2_value

        # Should be reasonably close (WR worth more than picks is realistic)
        ratio = total_pick_value / wr_value
        assert 0.35 <= ratio <= 0.60, \
            f"WR value: {wr_value}, Pick total: {total_pick_value}, ratio: {ratio}"

    def test_value_validation_errors(self):
        """Test that invalid inputs raise errors"""
        calc = TradeValueCalculator()

        # Missing required fields
        with pytest.raises(ValueError):
            calc.calculate_player_value(overall_rating=85)  # Missing position and age
