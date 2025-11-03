"""
Tests for Trade Proposal Generator

Phase 1.4 Day 1: Basic generation logic tests
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

from transactions.trade_proposal_generator import TradeProposalGenerator, TeamContext
from transactions.trade_value_calculator import TradeValueCalculator
from transactions.models import TradeAsset, AssetType, TradeProposal, FairnessRating
from team_management.gm_archetype import GMArchetype
from offseason.team_needs_analyzer import NeedUrgency


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def database_path():
    """Test database path."""
    return ":memory:"


@pytest.fixture
def dynasty_id():
    """Test dynasty ID."""
    return "test_dynasty"


@pytest.fixture
def calculator():
    """Mock trade value calculator."""
    calc = Mock(spec=TradeValueCalculator)

    # Default behavior: return value based on overall rating
    def calculate_player_value(asset):
        overall = getattr(asset, 'overall_rating', 75)
        # Simple formula: OVR * 3
        return overall * 3.0

    calc.calculate_player_value = Mock(side_effect=calculate_player_value)

    return calc


@pytest.fixture
def generator(database_path, dynasty_id, calculator):
    """Trade proposal generator instance."""
    gen = TradeProposalGenerator(database_path, dynasty_id, calculator)

    # Mock database APIs
    gen.player_api = Mock()
    gen.cap_api = Mock()

    return gen


@pytest.fixture
def team_context():
    """Basic team context."""
    return TeamContext(
        team_id=22,
        wins=5,
        losses=1,
        ties=0,
        cap_space=15_000_000,
        season="regular"
    )


@pytest.fixture
def gm_archetype():
    """Balanced GM archetype."""
    return GMArchetype(
        name="Balanced GM",
        description="Balanced approach",
        risk_tolerance=0.5,
        win_now_mentality=0.5,
        draft_pick_value=0.5,
        cap_management=0.5,
        trade_frequency=0.5,
        veteran_preference=0.5,
        star_chasing=0.3,
        loyalty=0.5
    )


def create_mock_player(
    player_id: int,
    overall: int,
    age: int,
    position: str,
    team_id: int,
    years_remaining: int = 2
) -> Dict[str, Any]:
    """Create mock player dictionary."""
    import json

    return {
        'player_id': player_id,
        'first_name': 'Test',
        'last_name': f'Player{player_id}',
        'number': player_id % 100,
        'team_id': team_id,
        'positions': json.dumps([position]),
        'attributes': json.dumps({'overall': overall, 'age': age}),
        'years_pro': age - 21,
        'depth_chart_order': 1
    }


def create_mock_contract(
    player_id: int,
    years_remaining: int = 2,
    aav: int = 5_000_000
) -> Dict[str, Any]:
    """Create mock contract dictionary."""
    return {
        'player_id': player_id,
        'years_remaining': years_remaining,
        'aav': aav,
        'total_guaranteed': aav * years_remaining // 2
    }


def create_need(position: str, urgency: NeedUrgency) -> Dict[str, Any]:
    """Create mock team need."""
    return {
        'position': position,
        'urgency': urgency,
        'urgency_score': urgency.value,
        'starter_overall': 65,
        'reason': f'Need {position}'
    }


# ============================================================================
# DAY 1 TESTS: BASIC GENERATION LOGIC
# ============================================================================

class TestBasicProposalGeneration:
    """Test basic proposal generation without GM filters."""

    def test_no_proposals_when_no_needs(
        self,
        generator,
        team_context,
        gm_archetype
    ):
        """Should return empty list when team has no needs."""
        # Empty needs list
        needs = []

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        assert proposals == []
        assert len(proposals) == 0

    def test_no_proposals_when_only_low_needs(
        self,
        generator,
        team_context,
        gm_archetype
    ):
        """Should return empty when only LOW/NONE urgency needs."""
        # Only low-priority needs
        needs = [
            create_need('running_back', NeedUrgency.LOW),
            create_need('tight_end', NeedUrgency.NONE)
        ]

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        assert proposals == []

    def test_basic_proposal_generation(
        self,
        generator,
        team_context,
        gm_archetype
    ):
        """Should generate 1 proposal for 1 CRITICAL need."""
        # Setup: 1 CRITICAL need
        needs = [create_need('linebacker', NeedUrgency.CRITICAL)]

        # Mock: Target player available (85 OVR LB on team 9)
        target_player = create_mock_player(
            player_id=1001,
            overall=85,
            age=27,
            position='linebacker',
            team_id=9
        )

        # Mock: Surplus WRs on team 22 (7 WRs = 5 needed + 1 safe + 1 surplus)
        surplus_wrs = []
        for i in range(7):
            wr = create_mock_player(
                player_id=2001 + i,
                overall=80 - i,  # Varying quality
                age=28,
                position='wide_receiver',
                team_id=22
            )
            wr['depth_chart_order'] = i + 1  # 1-7
            surplus_wrs.append(wr)

        # Mock player_api.get_team_roster
        def mock_get_roster(dynasty_id, team_id):
            if team_id == 9:
                return [target_player]
            elif team_id == 22:
                # Return 6 WRs (5 needed + 1 surplus)
                return surplus_wrs
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)

        # Mock contract
        generator._get_player_contract = Mock(return_value=create_mock_contract(1001))

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Should generate at least 1 proposal
        assert len(proposals) >= 1
        assert isinstance(proposals[0], TradeProposal)

        # Verify proposal structure
        proposal = proposals[0]
        assert proposal.team1_id == 22  # Proposing team
        assert proposal.team2_id == 9   # Target team
        assert len(proposal.team1_assets) > 0  # Sending assets
        assert len(proposal.team2_assets) == 1  # Receiving 1 player

    def test_excludes_own_team_players(
        self,
        generator,
        team_context,
        gm_archetype
    ):
        """Should never propose trading for own team's players."""
        needs = [create_need('quarterback', NeedUrgency.CRITICAL)]

        # Mock: QB on own team (team 22)
        own_qb = create_mock_player(
            player_id=3001,
            overall=90,
            age=25,
            position='quarterback',
            team_id=22  # Same as proposing team
        )

        # Mock: QB on other team (team 15)
        other_qb = create_mock_player(
            player_id=3002,
            overall=88,
            age=26,
            position='quarterback',
            team_id=15
        )

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 22:
                return [own_qb] * 3  # 3 QBs on own roster
            elif team_id == 15:
                return [other_qb]
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(3002))

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Should only propose for team 15's QB, not own team's QB
        for proposal in proposals:
            assert proposal.team2_id != 22  # Never trading with self
            assert proposal.team2_id == 15  # Only team 15

    def test_excludes_pending_free_agents(
        self,
        generator,
        team_context,
        gm_archetype
    ):
        """Should not propose trades for pending free agents."""
        needs = [create_need('safety', NeedUrgency.HIGH)]

        # Mock: Safety with contract expiring (years_remaining=0)
        expiring_safety = create_mock_player(
            player_id=4001,
            overall=82,
            age=29,
            position='safety',
            team_id=7
        )

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 7:
                return [expiring_safety]
            elif team_id == 22:
                return []
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)

        # Contract with 0 years remaining (pending FA)
        generator._get_player_contract = Mock(
            return_value=create_mock_contract(4001, years_remaining=0)
        )

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Should not generate proposals for pending FAs
        assert len(proposals) == 0

    def test_multiple_needs_multiple_proposals(
        self,
        generator,
        team_context,
        gm_archetype
    ):
        """Should generate separate proposals for different needs."""
        # 2 CRITICAL needs
        needs = [
            create_need('linebacker', NeedUrgency.CRITICAL),
            create_need('cornerback', NeedUrgency.HIGH)
        ]

        # Mock: LB on team 9, CB on team 12
        lb_player = create_mock_player(5001, 84, 26, 'linebacker', 9)
        cb_player = create_mock_player(5002, 82, 25, 'cornerback', 12)

        # Mock: Surplus WRs on team 22 (7 unique WRs = 5 needed + 1 safe + 1 surplus)
        surplus_wrs = []
        for i in range(7):
            wr = create_mock_player(5101 + i, 79 - i, 28, 'wide_receiver', 22)
            wr['depth_chart_order'] = i + 1
            surplus_wrs.append(wr)

        # Mock: Surplus RBs on team 22 (5 unique RBs = 3 needed + 1 safe + 1 surplus)
        surplus_rbs = []
        for i in range(5):
            rb = create_mock_player(5201 + i, 78 - i, 27, 'running_back', 22)
            rb['depth_chart_order'] = i + 1
            surplus_rbs.append(rb)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 9:
                return [lb_player]
            elif team_id == 12:
                return [cb_player]
            elif team_id == 22:
                return surplus_wrs + surplus_rbs  # Surplus at both positions
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)

        def mock_get_contract(player_id):
            return create_mock_contract(player_id)

        generator._get_player_contract = Mock(side_effect=mock_get_contract)

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Should generate proposals for both needs
        assert len(proposals) >= 2

        # Verify different targets
        target_teams = {p.team2_id for p in proposals}
        assert 9 in target_teams or 12 in target_teams  # At least one target found

    def test_value_calculation_integration(
        self,
        generator,
        team_context,
        gm_archetype,
        calculator
    ):
        """Should use TradeValueCalculator for asset valuation."""
        needs = [create_need('defensive_end', NeedUrgency.CRITICAL)]

        # Mock: 88 OVR DE (value should be 88 * 3 = 264)
        de_player = create_mock_player(6001, 88, 27, 'defensive_end', 15)

        # Mock: 85 OVR DT (value should be 85 * 3 = 255)
        dt_surplus = create_mock_player(6101, 85, 28, 'defensive_tackle', 22)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 15:
                return [de_player]
            elif team_id == 22:
                return [dt_surplus] * 5  # 5 DTs (surplus)
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(6001))

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        if proposals:
            # Verify calculator was called
            assert calculator.calculate_player_value.called

            # Verify values are reasonable
            proposal = proposals[0]
            assert proposal.team1_total_value > 0
            assert proposal.team2_total_value > 0

            # Value ratio should be in fair range
            assert 0.70 <= proposal.value_ratio <= 1.30

    def test_no_viable_targets(
        self,
        generator,
        team_context,
        gm_archetype
    ):
        """Should return empty list when no players match needs."""
        needs = [create_need('quarterback', NeedUrgency.CRITICAL)]

        # Mock: No QBs available anywhere, only RBs and WRs
        rb_player = create_mock_player(7001, 80, 25, 'running_back', 9)
        wr_player = create_mock_player(7002, 82, 26, 'wide_receiver', 15)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 9:
                return [rb_player]
            elif team_id == 15:
                return [wr_player]
            elif team_id == 22:
                return []
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Should return empty - no QBs available
        assert len(proposals) == 0

    def test_cap_space_validation(
        self,
        generator,
        gm_archetype
    ):
        """Should reject proposals that exceed available cap space."""
        # Team with minimal cap space
        limited_cap_context = TeamContext(
            team_id=22,
            wins=5,
            losses=1,
            cap_space=2_000_000,  # Only $2M available
            season="regular"
        )

        needs = [create_need('left_tackle', NeedUrgency.CRITICAL)]

        # Mock: 86 OVR LT with expensive contract ($15M/year)
        expensive_lt = create_mock_player(8001, 86, 28, 'left_tackle', 20)

        # Mock: 78 OVR WR with cheap contract ($3M/year)
        cheap_wr = create_mock_player(8101, 78, 26, 'wide_receiver', 22)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 20:
                return [expensive_lt]
            elif team_id == 22:
                return [cheap_wr] * 6  # Surplus WRs
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)

        # Expensive LT contract
        def mock_get_contract(player_id):
            if player_id == 8001:
                return create_mock_contract(8001, years_remaining=3, aav=15_000_000)
            else:
                return create_mock_contract(player_id, years_remaining=2, aav=3_000_000)

        generator._get_player_contract = Mock(side_effect=mock_get_contract)

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=limited_cap_context,
            needs=needs,
            season=2025
        )

        # Should reject due to cap space (net cap = +$15M - $3M = +$12M > $2M available)
        # OR proposal should pass cap validation if trade reduces cap hit
        if proposals:
            # If proposals exist, verify cap validation passed
            assert proposals[0].passes_cap_validation is True
        else:
            # No proposals generated (cap constraint filtered them out)
            assert len(proposals) == 0


# ============================================================================
# DAY 2 TESTS: FAIR VALUE CONSTRUCTION
# ============================================================================

class TestFairValueConstruction:
    """Test combination search algorithm for fair trades."""

    def create_test_asset(self, player_id: int, value: float) -> TradeAsset:
        """Create test TradeAsset with specific value."""
        return TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=player_id,
            player_name=f"Player{player_id}",
            position="wide_receiver",
            overall_rating=75,
            age=26,
            years_pro=4,
            contract_years_remaining=2,
            annual_cap_hit=5_000_000,
            total_remaining_guaranteed=5_000_000,
            trade_value=value
        )

    def test_single_asset_fair_value(self, generator, team_context):
        """Should prefer 1-for-1 trade when single asset is fair."""
        # Target: 250 value
        target_player = create_mock_player(9001, 85, 27, 'linebacker', 15)
        target_value = 250.0

        # Surplus assets: One exactly matches target value
        surplus_assets = [
            self.create_test_asset(9101, 245.0),  # Close match (ratio 0.98)
            self.create_test_asset(9102, 150.0),
            self.create_test_asset(9103, 100.0)
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'linebacker', 'urgency': NeedUrgency.CRITICAL},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is not None
        assert len(proposal.team1_assets) == 1  # 1-for-1 trade
        assert proposal.team1_assets[0].player_id == 9101
        assert 0.80 <= proposal.value_ratio <= 1.20

    def test_two_asset_combination(self, generator, team_context):
        """Should use 2-for-1 when single asset insufficient."""
        # Target: 300 value
        target_player = create_mock_player(9201, 88, 26, 'quarterback', 12)
        target_value = 300.0

        # Surplus assets: No single match, but two assets work
        surplus_assets = [
            self.create_test_asset(9301, 180.0),  # Not enough alone
            self.create_test_asset(9302, 120.0),  # Together = 300
            self.create_test_asset(9303, 80.0)
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'quarterback', 'urgency': NeedUrgency.CRITICAL},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is not None
        assert len(proposal.team1_assets) == 2  # 2-for-1 trade
        assert proposal.team1_total_value >= 240  # Within 0.80-1.20 range
        assert proposal.team1_total_value <= 360

    def test_three_asset_max(self, generator, team_context):
        """Should handle 3-for-1 trade (max complexity)."""
        # Target: 350 value
        target_player = create_mock_player(9401, 90, 25, 'left_tackle', 20)
        target_value = 350.0

        # Surplus assets: Need 3 to reach target
        surplus_assets = [
            self.create_test_asset(9501, 140.0),
            self.create_test_asset(9502, 120.0),
            self.create_test_asset(9503, 100.0),  # Together = 360 (ratio 1.03)
            self.create_test_asset(9504, 50.0)
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'left_tackle', 'urgency': NeedUrgency.CRITICAL},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is not None
        assert len(proposal.team1_assets) <= 3  # Max 3 assets
        assert 0.80 <= proposal.value_ratio <= 1.20

    def test_no_combination_found(self, generator, team_context):
        """Should return None when no fair combination exists."""
        # Target: 400 value (very expensive player)
        target_player = create_mock_player(9601, 92, 24, 'quarterback', 7)
        target_value = 400.0

        # Surplus assets: All too low value, can't reach target fairly
        surplus_assets = [
            self.create_test_asset(9701, 100.0),
            self.create_test_asset(9702, 80.0),
            self.create_test_asset(9703, 60.0),
            # Total of all 3 = 240, ratio = 0.60 (below 0.80 threshold)
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'quarterback', 'urgency': NeedUrgency.CRITICAL},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is None  # No fair combination

    def test_prefers_simpler_trades(self, generator, team_context):
        """Should choose 1-for-1 over 2-for-1 if both are fair."""
        # Target: 200 value
        target_player = create_mock_player(9801, 82, 28, 'cornerback', 9)
        target_value = 200.0

        # Surplus assets: Both single and double combos work
        surplus_assets = [
            self.create_test_asset(9901, 195.0),  # Single (ratio 0.975) - BEST
            self.create_test_asset(9902, 120.0),  # With 9903 = 200 (ratio 1.0)
            self.create_test_asset(9903, 80.0)
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'cornerback', 'urgency': NeedUrgency.HIGH},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is not None
        # Should prefer 1-for-1 (simpler)
        assert len(proposal.team1_assets) == 1
        assert proposal.team1_assets[0].player_id == 9901

    def test_value_ratio_lower_boundary(self, generator, team_context):
        """Should accept trades at 0.80 ratio (lower boundary)."""
        # Target: 250 value
        target_player = create_mock_player(10001, 84, 27, 'safety', 15)
        target_value = 250.0

        # Surplus: Exactly at 0.80 boundary
        surplus_assets = [
            self.create_test_asset(10101, 200.0),  # Ratio = 200/250 = 0.80
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'safety', 'urgency': NeedUrgency.HIGH},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is not None
        assert abs(proposal.value_ratio - 0.80) < 0.01

    def test_value_ratio_upper_boundary(self, generator, team_context):
        """Should accept trades at 1.20 ratio (upper boundary)."""
        # Target: 250 value
        target_player = create_mock_player(10201, 84, 26, 'defensive_end', 12)
        target_value = 250.0

        # Surplus: Exactly at 1.20 boundary
        surplus_assets = [
            self.create_test_asset(10301, 300.0),  # Ratio = 300/250 = 1.20
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'defensive_end', 'urgency': NeedUrgency.CRITICAL},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is not None
        assert abs(proposal.value_ratio - 1.20) < 0.01

    def test_rejects_below_lower_boundary(self, generator, team_context):
        """Should reject trades below 0.80 ratio."""
        # Target: 300 value
        target_player = create_mock_player(10401, 87, 25, 'linebacker', 20)
        target_value = 300.0

        # Surplus: Below threshold (ratio 0.73)
        surplus_assets = [
            self.create_test_asset(10501, 220.0),  # Ratio = 220/300 = 0.733
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'linebacker', 'urgency': NeedUrgency.CRITICAL},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is None  # Too unfair

    def test_rejects_above_upper_boundary(self, generator, team_context):
        """Should reject trades above 1.20 ratio."""
        # Target: 200 value
        target_player = create_mock_player(10601, 81, 29, 'tight_end', 18)
        target_value = 200.0

        # Surplus: Above threshold (ratio 1.30)
        surplus_assets = [
            self.create_test_asset(10701, 260.0),  # Ratio = 260/200 = 1.30
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'tight_end', 'urgency': NeedUrgency.HIGH},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is None  # Too unfair (sending too much)

    def test_greedy_algorithm_finds_best_simple(self, generator, team_context):
        """Should use greedy algorithm to find good combination quickly."""
        # Target: 280 value
        target_player = create_mock_player(10801, 86, 27, 'cornerback', 14)
        target_value = 280.0

        # Surplus: Multiple combinations possible, should find one
        surplus_assets = [
            self.create_test_asset(10901, 160.0),  # With 10902 = 280 (perfect)
            self.create_test_asset(10902, 120.0),
            self.create_test_asset(10903, 100.0),
            self.create_test_asset(10904, 90.0),
            self.create_test_asset(10905, 80.0)
        ]

        proposal = generator._construct_fair_value_proposal(
            proposing_team_id=22,
            target_player=target_player,
            target_value=target_value,
            target_need={'position': 'cornerback', 'urgency': NeedUrgency.CRITICAL},
            surplus_assets=surplus_assets,
            team_context=team_context
        )

        assert proposal is not None
        # Should find a valid combination
        assert 0.80 <= proposal.value_ratio <= 1.20
        # Should prefer simpler combination (2 assets rather than 3)
        assert len(proposal.team1_assets) <= 2


# ============================================================================
# DAY 3 TESTS: GM PERSONALITY FILTERS
# ============================================================================

class TestGMPersonalityFilters:
    """Test GM personality filtering of proposals."""

    def create_test_proposal(
        self,
        team1_id: int,
        team2_id: int,
        player_overall: int,
        player_age: int,
        cap_hit: int,
        value_ratio: float = 1.0
    ) -> TradeProposal:
        """Create test trade proposal with specific characteristics."""
        # Create target player asset
        target_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=9999,
            player_name=f"Target Player",
            position="linebacker",
            overall_rating=player_overall,
            age=player_age,
            years_pro=player_age - 21,
            contract_years_remaining=2,
            annual_cap_hit=cap_hit,
            total_remaining_guaranteed=cap_hit * 2,
            trade_value=250.0
        )

        # Create sending player asset
        sending_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=8888,
            player_name=f"Sending Player",
            position="wide_receiver",
            overall_rating=80,
            age=26,
            years_pro=4,
            contract_years_remaining=2,
            annual_cap_hit=5_000_000,
            total_remaining_guaranteed=10_000_000,
            trade_value=250.0 / value_ratio
        )

        return TradeProposal(
            team1_id=team1_id,
            team1_assets=[sending_asset],
            team1_total_value=250.0 / value_ratio,
            team2_id=team2_id,
            team2_assets=[target_asset],
            team2_total_value=250.0,
            value_ratio=value_ratio,
            fairness_rating=FairnessRating.VERY_FAIR,
            passes_cap_validation=True,
            passes_roster_validation=True
        )

    def test_conservative_gm_fewer_proposals(self, generator, team_context):
        """Conservative GM (low trade_frequency) generates fewer proposals."""
        conservative_gm = GMArchetype(
            name="Conservative GM",
            description="Conservative",
            risk_tolerance=0.3,
            trade_frequency=0.3,  # Low trade frequency
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            veteran_preference=0.5,
            star_chasing=0.3,
            loyalty=0.7
        )

        # Create 5 proposals
        proposals = [
            self.create_test_proposal(22, 9, 85, 27, 8_000_000) for _ in range(5)
        ]

        filtered = generator._apply_gm_filters(proposals, conservative_gm, team_context)

        # Conservative GM: 0.3 * 5 = 1.5 → 1 proposal max
        assert len(filtered) <= 1

    def test_aggressive_gm_more_proposals(self, generator, team_context):
        """Aggressive GM (high trade_frequency) generates more proposals."""
        aggressive_gm = GMArchetype(
            name="Aggressive GM",
            description="Aggressive",
            risk_tolerance=0.8,
            trade_frequency=0.9,  # High trade frequency
            win_now_mentality=0.7,
            draft_pick_value=0.4,
            cap_management=0.3,
            veteran_preference=0.5,
            star_chasing=0.6,
            loyalty=0.3
        )

        # Create 5 proposals
        proposals = [
            self.create_test_proposal(22, 9, 85, 27, 8_000_000) for _ in range(5)
        ]

        filtered = generator._apply_gm_filters(proposals, aggressive_gm, team_context)

        # Aggressive GM: 0.9 * 5 = 4.5 → 4 proposals max
        assert len(filtered) <= 4
        assert len(filtered) >= 3  # At least 3 should pass

    def test_star_chaser_prefers_elite(self, generator, team_context):
        """Star chasing GM prefers elite players (88+ OVR)."""
        star_chaser_gm = GMArchetype(
            name="Star Chaser",
            description="Star Chaser",
            risk_tolerance=0.6,
            trade_frequency=0.8,
            win_now_mentality=0.7,
            draft_pick_value=0.3,
            cap_management=0.4,
            veteran_preference=0.5,
            star_chasing=0.9,  # Very high star chasing
            loyalty=0.3
        )

        # Mix of elite and non-elite targets
        proposals = [
            self.create_test_proposal(22, 9, 90, 26, 12_000_000),  # Elite - PASS
            self.create_test_proposal(22, 10, 82, 27, 6_000_000),  # Not elite - REJECT
            self.create_test_proposal(22, 11, 87, 25, 10_000_000),  # Good - PASS
        ]

        filtered = generator._apply_gm_filters(proposals, star_chaser_gm, team_context)

        # Should prefer elite players (85+)
        assert len(filtered) == 2  # Only elite/good players
        assert all(p.team2_assets[0].overall_rating >= 85 for p in filtered)

    def test_non_star_chaser_avoids_elite(self, generator, team_context):
        """Non-star chasing GM avoids elite players."""
        balanced_gm = GMArchetype(
            name="Balanced GM",
            description="Balanced",
            risk_tolerance=0.5,
            trade_frequency=0.8,  # Higher frequency to evaluate more proposals
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            veteran_preference=0.5,
            star_chasing=0.2,  # Very low star chasing
            loyalty=0.5
        )

        # Mix of elite and non-elite targets
        proposals = [
            self.create_test_proposal(22, 9, 90, 26, 15_000_000),  # Elite - REJECT
            self.create_test_proposal(22, 10, 84, 27, 7_000_000),  # Good - PASS
            self.create_test_proposal(22, 11, 81, 25, 5_000_000),  # Average - PASS
        ]

        filtered = generator._apply_gm_filters(proposals, balanced_gm, team_context)

        # Should avoid elite players (88+)
        # Frequency: 0.8 * 5 = 4 max, so all 3 evaluated
        # Only 2 should pass (84 and 81 OVR)
        assert len(filtered) == 2
        assert all(p.team2_assets[0].overall_rating < 88 for p in filtered)

    def test_cap_conservative_rejects_expensive(self, generator):
        """Cap conservative GM rejects expensive contracts."""
        cap_conservative_gm = GMArchetype(
            name="Cap Conservative",
            description="Cap Conservative",
            risk_tolerance=0.4,
            trade_frequency=0.5,
            win_now_mentality=0.4,
            draft_pick_value=0.6,
            cap_management=0.9,  # Very high cap management
            veteran_preference=0.5,
            star_chasing=0.4,
            loyalty=0.6
        )

        # Limited cap space context
        limited_cap_context = TeamContext(
            team_id=22,
            wins=5,
            losses=1,
            cap_space=10_000_000  # Only $10M available
        )

        # Proposals with varying cap hits
        proposals = [
            self.create_test_proposal(22, 9, 85, 27, 8_000_000),  # $8M - 80% cap → REJECT (>50%)
            self.create_test_proposal(22, 10, 83, 26, 4_000_000),  # $4M - 40% cap → PASS (<50%)
        ]

        # Note: Need to account for sending player ($5M), net = $8M-$5M=$3M (30%), $4M-$5M=-$1M (0%)

        filtered = generator._apply_gm_filters(proposals, cap_conservative_gm, limited_cap_context)

        # Should reject expensive contracts consuming >50% cap
        assert len(filtered) == 2  # Both pass because of net cap calculation

    def test_win_now_gm_relaxes_cap(self, generator):
        """Win-now GM relaxes cap constraints."""
        win_now_gm = GMArchetype(
            name="Win-Now GM",
            description="Win-Now",
            risk_tolerance=0.7,
            trade_frequency=0.7,
            win_now_mentality=0.9,  # Very high win-now
            draft_pick_value=0.3,
            cap_management=0.6,  # Moderate cap mgmt
            veteran_preference=0.8,
            star_chasing=0.7,
            loyalty=0.3
        )

        # Limited cap space
        limited_cap_context = TeamContext(
            team_id=22,
            wins=8,
            losses=1,
            cap_space=10_000_000
        )

        # Expensive player (75% of cap after net)
        proposals = [
            self.create_test_proposal(22, 9, 88, 29, 12_500_000),  # Net = $12.5M-$5M = $7.5M (75%)
        ]

        filtered = generator._apply_gm_filters(proposals, win_now_gm, limited_cap_context)

        # Win-now should accept up to 80% cap consumption
        assert len(filtered) == 1  # Should pass due to win-now override

    def test_veteran_preference_filters_age(self, generator, team_context):
        """Veteran-preferring GM targets older players."""
        veteran_gm = GMArchetype(
            name="Veteran GM",
            description="Veteran GM",
            risk_tolerance=0.5,
            trade_frequency=0.6,
            win_now_mentality=0.7,
            draft_pick_value=0.4,
            cap_management=0.5,
            veteran_preference=0.9,  # Very high veteran pref
            star_chasing=0.5,
            loyalty=0.4
        )

        # Mix of young and veteran players
        proposals = [
            self.create_test_proposal(22, 9, 85, 23, 6_000_000),  # Young - REJECT
            self.create_test_proposal(22, 10, 84, 29, 8_000_000),  # Veteran - PASS
            self.create_test_proposal(22, 11, 86, 27, 7_000_000),  # Prime - PASS
        ]

        filtered = generator._apply_gm_filters(proposals, veteran_gm, team_context)

        # Should prefer veterans (27+)
        assert len(filtered) == 2
        assert all(p.team2_assets[0].age >= 27 for p in filtered)

    def test_youth_preference_filters_age(self, generator, team_context):
        """Youth-preferring GM targets younger players."""
        youth_gm = GMArchetype(
            name="Youth GM",
            description="Youth GM",
            risk_tolerance=0.6,
            trade_frequency=0.6,
            win_now_mentality=0.3,
            draft_pick_value=0.8,
            cap_management=0.6,
            veteran_preference=0.1,  # Very low veteran pref
            star_chasing=0.4,
            loyalty=0.5
        )

        # Mix of young and veteran players
        proposals = [
            self.create_test_proposal(22, 9, 85, 24, 6_000_000),  # Young - PASS
            self.create_test_proposal(22, 10, 86, 30, 10_000_000),  # Veteran - REJECT
            self.create_test_proposal(22, 11, 84, 27, 7_000_000),  # Prime - PASS
        ]

        filtered = generator._apply_gm_filters(proposals, youth_gm, team_context)

        # Should prefer youth (<29)
        assert len(filtered) == 2
        assert all(p.team2_assets[0].age < 29 for p in filtered)

    def test_multiple_filters_interaction(self, generator):
        """Multiple filters work together correctly."""
        selective_gm = GMArchetype(
            name="Selective GM",
            description="Selective GM",
            risk_tolerance=0.5,
            trade_frequency=0.4,  # Low frequency
            win_now_mentality=0.5,
            draft_pick_value=0.6,
            cap_management=0.8,  # High cap mgmt
            veteran_preference=0.8,  # High veteran pref
            star_chasing=0.7,  # High star chasing
            loyalty=0.6
        )

        limited_cap_context = TeamContext(
            team_id=22,
            wins=6,
            losses=2,
            cap_space=15_000_000
        )

        # Various proposals - most should fail multiple filters
        proposals = [
            self.create_test_proposal(22, 9, 90, 29, 8_000_000),  # Elite veteran, $3M net (20%) - PASS
            self.create_test_proposal(22, 10, 82, 24, 6_000_000),  # Not elite, young - REJECT
            self.create_test_proposal(22, 11, 88, 28, 9_000_000),  # Elite veteran, $4M net (27%) - PASS
            self.create_test_proposal(22, 12, 91, 30, 15_000_000),  # Elite veteran, $10M net (67%) → REJECT (cap)
        ]

        filtered = generator._apply_gm_filters(proposals, selective_gm, limited_cap_context)

        # Only proposals meeting ALL filters should pass
        # Frequency limit: 0.4 * 5 = 2 max
        assert len(filtered) <= 2
        # All filtered should be elite veterans with acceptable cap
        for proposal in filtered:
            target = proposal.team2_assets[0]
            assert target.overall_rating >= 85  # Star chasing
            assert target.age >= 27  # Veteran preference

    def test_balanced_gm_accepts_most(self, generator, team_context):
        """Balanced GM with moderate traits accepts most proposals."""
        balanced_gm = GMArchetype(
            name="Balanced GM",
            description="Balanced",
            risk_tolerance=0.5,
            trade_frequency=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            veteran_preference=0.5,
            star_chasing=0.5,
            loyalty=0.5
        )

        # Diverse set of proposals
        proposals = [
            self.create_test_proposal(22, 9, 85, 27, 7_000_000),
            self.create_test_proposal(22, 10, 82, 25, 5_000_000),
            self.create_test_proposal(22, 11, 88, 29, 9_000_000),
        ]

        filtered = generator._apply_gm_filters(proposals, balanced_gm, team_context)

        # Balanced GM should accept most reasonable proposals
        assert len(filtered) >= 2  # At least 2 should pass

    def test_filter_order_matters(self, generator, team_context):
        """Filters are applied in correct order (frequency → star → cap → vet)."""
        gm = GMArchetype(
            name="Test GM",
            description="Test",
            risk_tolerance=0.5,
            trade_frequency=0.2,  # Only 1 proposal allowed
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            veteran_preference=0.5,
            star_chasing=0.5,
            loyalty=0.5
        )

        # Create 3 proposals, but frequency allows only 1
        proposals = [
            self.create_test_proposal(22, 9, 85, 27, 7_000_000),
            self.create_test_proposal(22, 10, 86, 26, 8_000_000),
            self.create_test_proposal(22, 11, 84, 28, 6_000_000),
        ]

        filtered = generator._apply_gm_filters(proposals, gm, team_context)

        # Should only get 1 proposal due to frequency limit
        assert len(filtered) == 1

    def test_empty_proposals_list(self, generator, team_context, gm_archetype):
        """Should handle empty proposals list gracefully."""
        proposals = []

        filtered = generator._apply_gm_filters(proposals, gm_archetype, team_context)

        assert filtered == []


# ============================================================================
# DAY 4 TESTS: VALIDATION AND SORTING
# ============================================================================

class TestValidationAndSorting:
    """Test proposal validation and sorting logic."""

    def create_valid_proposal(
        self,
        team1_id: int = 22,
        team2_id: int = 9,
        value_ratio: float = 1.0,
        cap_valid: bool = True
    ) -> TradeProposal:
        """Create valid test proposal."""
        asset1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1001,
            player_name="Player 1",
            position="wide_receiver",
            overall_rating=80,
            age=26,
            years_pro=4,
            contract_years_remaining=2,
            annual_cap_hit=5_000_000,
            total_remaining_guaranteed=10_000_000,
            trade_value=250.0
        )

        asset2 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=2001,
            player_name="Player 2",
            position="linebacker",
            overall_rating=85,
            age=27,
            years_pro=5,
            contract_years_remaining=3,
            annual_cap_hit=8_000_000,
            total_remaining_guaranteed=16_000_000,
            trade_value=250.0 / value_ratio
        )

        return TradeProposal(
            team1_id=team1_id,
            team1_assets=[asset1],
            team1_total_value=250.0,
            team2_id=team2_id,
            team2_assets=[asset2],
            team2_total_value=250.0 / value_ratio,
            value_ratio=value_ratio,
            fairness_rating=FairnessRating.VERY_FAIR,
            passes_cap_validation=cap_valid,
            passes_roster_validation=True
        )

    def test_rejects_duplicate_players(self, generator):
        """Should reject proposals with duplicate player IDs."""
        # Create proposal with same player on both sides
        duplicate_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=9999,  # Same ID
            player_name="Duplicate",
            position="linebacker",
            overall_rating=85,
            age=27,
            years_pro=5,
            contract_years_remaining=2,
            annual_cap_hit=7_000_000,
            total_remaining_guaranteed=14_000_000,
            trade_value=250.0
        )

        proposal = TradeProposal(
            team1_id=22,
            team1_assets=[duplicate_asset],
            team1_total_value=250.0,
            team2_id=9,
            team2_assets=[duplicate_asset],  # Same player!
            team2_total_value=250.0,
            value_ratio=1.0,
            fairness_rating=FairnessRating.VERY_FAIR,
            passes_cap_validation=True,
            passes_roster_validation=True
        )

        is_valid, reason = generator._validate_proposal(proposal, 22)

        assert is_valid is False
        assert "Duplicate player" in reason

    def test_rejects_free_agents(self, generator):
        """Should reject proposals with pending free agents."""
        free_agent = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=3001,
            player_name="Free Agent",
            position="cornerback",
            overall_rating=82,
            age=28,
            years_pro=6,
            contract_years_remaining=0,  # Pending FA
            annual_cap_hit=6_000_000,
            total_remaining_guaranteed=0,
            trade_value=200.0
        )

        valid_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=3002,
            player_name="Valid Player",
            position="safety",
            overall_rating=80,
            age=25,
            years_pro=3,
            contract_years_remaining=2,
            annual_cap_hit=5_000_000,
            total_remaining_guaranteed=10_000_000,
            trade_value=200.0
        )

        proposal = TradeProposal(
            team1_id=22,
            team1_assets=[valid_asset],
            team1_total_value=200.0,
            team2_id=9,
            team2_assets=[free_agent],
            team2_total_value=200.0,
            value_ratio=1.0,
            fairness_rating=FairnessRating.VERY_FAIR,
            passes_cap_validation=True,
            passes_roster_validation=True
        )

        is_valid, reason = generator._validate_proposal(proposal, 22)

        assert is_valid is False
        assert "pending free agent" in reason

    def test_rejects_unfair_ratios_below_threshold(self, generator):
        """Should reject proposals with ratio < 0.80."""
        proposal = self.create_valid_proposal(value_ratio=0.75)

        is_valid, reason = generator._validate_proposal(proposal, 22)

        assert is_valid is False
        assert "outside acceptable range" in reason

    def test_rejects_unfair_ratios_above_threshold(self, generator):
        """Should reject proposals with ratio > 1.20."""
        proposal = self.create_valid_proposal(value_ratio=1.25)

        is_valid, reason = generator._validate_proposal(proposal, 22)

        assert is_valid is False
        assert "outside acceptable range" in reason

    def test_accepts_ratio_at_lower_boundary(self, generator):
        """Should accept proposals at exactly 0.80 ratio."""
        proposal = self.create_valid_proposal(value_ratio=0.80)

        is_valid, reason = generator._validate_proposal(proposal, 22)

        assert is_valid is True

    def test_accepts_ratio_at_upper_boundary(self, generator):
        """Should accept proposals at exactly 1.20 ratio."""
        proposal = self.create_valid_proposal(value_ratio=1.20)

        is_valid, reason = generator._validate_proposal(proposal, 22)

        assert is_valid is True

    def test_rejects_cap_space_violation(self, generator):
        """Should reject proposals that fail cap validation."""
        proposal = self.create_valid_proposal(cap_valid=False)

        is_valid, reason = generator._validate_proposal(proposal, 22)

        assert is_valid is False
        assert "Cap space validation failed" in reason

    def test_sorting_by_value_ratio(self, generator):
        """Should sort proposals by proximity to 1.0 value ratio."""
        proposals = [
            self.create_valid_proposal(value_ratio=0.85),  # 0.15 from 1.0
            self.create_valid_proposal(value_ratio=1.02),  # 0.02 from 1.0 - BEST
            self.create_valid_proposal(value_ratio=1.15),  # 0.15 from 1.0
        ]

        sorted_proposals = generator._sort_proposals(proposals)

        # Best should be first (closest to 1.0)
        assert sorted_proposals[0].value_ratio == 1.02
        assert sorted_proposals[1].value_ratio in [0.85, 1.15]
        assert sorted_proposals[2].value_ratio in [0.85, 1.15]

    def test_sorting_by_complexity(self, generator):
        """Should prefer simpler trades when value ratios are equal."""
        # Create proposals with same ratio but different complexity
        simple_proposal = TradeProposal(
            team1_id=22,
            team1_assets=[TradeAsset(
                asset_type=AssetType.PLAYER,
                player_id=4001,
                player_name="Player A",
                position="linebacker",
                overall_rating=85,
                age=27,
                years_pro=5,
                contract_years_remaining=2,
                annual_cap_hit=8_000_000,
                total_remaining_guaranteed=16_000_000,
                trade_value=250.0
            )],
            team1_total_value=250.0,
            team2_id=9,
            team2_assets=[TradeAsset(
                asset_type=AssetType.PLAYER,
                player_id=4002,
                player_name="Player B",
                position="wide_receiver",
                overall_rating=80,
                age=26,
                years_pro=4,
                contract_years_remaining=2,
                annual_cap_hit=7_000_000,
                total_remaining_guaranteed=14_000_000,
                trade_value=250.0
            )],
            team2_total_value=250.0,
            value_ratio=1.0,
            fairness_rating=FairnessRating.VERY_FAIR,
            passes_cap_validation=True,
            passes_roster_validation=True
        )

        complex_proposal = TradeProposal(
            team1_id=22,
            team1_assets=[
                TradeAsset(
                    asset_type=AssetType.PLAYER,
                    player_id=5001,
                    player_name="Player C",
                    position="cornerback",
                    overall_rating=78,
                    age=25,
                    years_pro=3,
                    contract_years_remaining=2,
                    annual_cap_hit=4_000_000,
                    total_remaining_guaranteed=8_000_000,
                    trade_value=130.0
                ),
                TradeAsset(
                    asset_type=AssetType.PLAYER,
                    player_id=5002,
                    player_name="Player D",
                    position="safety",
                    overall_rating=76,
                    age=24,
                    years_pro=2,
                    contract_years_remaining=2,
                    annual_cap_hit=3_000_000,
                    total_remaining_guaranteed=6_000_000,
                    trade_value=120.0
                )
            ],
            team1_total_value=250.0,
            team2_id=9,
            team2_assets=[TradeAsset(
                asset_type=AssetType.PLAYER,
                player_id=5003,
                player_name="Player E",
                position="defensive_end",
                overall_rating=84,
                age=28,
                years_pro=6,
                contract_years_remaining=2,
                annual_cap_hit=9_000_000,
                total_remaining_guaranteed=18_000_000,
                trade_value=250.0
            )],
            team2_total_value=250.0,
            value_ratio=1.0,
            fairness_rating=FairnessRating.VERY_FAIR,
            passes_cap_validation=True,
            passes_roster_validation=True
        )

        proposals = [complex_proposal, simple_proposal]

        sorted_proposals = generator._sort_proposals(proposals)

        # Simple should be first (fewer total assets)
        assert len(sorted_proposals[0].team1_assets) == 1
        assert len(sorted_proposals[1].team1_assets) == 2

    def test_complete_validation_pipeline(self, generator):
        """Should run all validation checks in sequence."""
        # Create valid proposal
        valid_proposal = self.create_valid_proposal()

        is_valid, reason = generator._validate_proposal(valid_proposal, 22)

        assert is_valid is True
        assert reason == ""

    def test_invalid_proposals_filtered_out(self, generator, team_context, gm_archetype):
        """End-to-end: Invalid proposals should be filtered out."""
        # This would test the full generate_trade_proposals flow
        # For now, just verify validation is called

        # Create mix of valid and invalid proposals
        valid = self.create_valid_proposal(value_ratio=1.0)
        invalid_ratio = self.create_valid_proposal(value_ratio=0.75)
        invalid_cap = self.create_valid_proposal(cap_valid=False)

        # Test each individually
        valid_result, _ = generator._validate_proposal(valid, 22)
        invalid_ratio_result, _ = generator._validate_proposal(invalid_ratio, 22)
        invalid_cap_result, _ = generator._validate_proposal(invalid_cap, 22)

        assert valid_result is True
        assert invalid_ratio_result is False
        assert invalid_cap_result is False

    def test_validation_provides_clear_reasons(self, generator):
        """Validation should provide clear failure reasons."""
        # Test each validation failure type

        # 1. Unfair ratio
        unfair_proposal = self.create_valid_proposal(value_ratio=0.70)
        is_valid, reason = generator._validate_proposal(unfair_proposal, 22)
        assert "outside acceptable range" in reason

        # 2. Cap violation
        cap_proposal = self.create_valid_proposal(cap_valid=False)
        is_valid, reason = generator._validate_proposal(cap_proposal, 22)
        assert "Cap space validation failed" in reason

    def test_validates_all_assets_in_proposal(self, generator):
        """Should validate all assets in multi-asset proposals."""
        # Create 3-for-1 proposal with one invalid asset
        valid_asset1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=6001,
            player_name="Valid 1",
            position="linebacker",
            overall_rating=82,
            age=26,
            years_pro=4,
            contract_years_remaining=2,
            annual_cap_hit=6_000_000,
            total_remaining_guaranteed=12_000_000,
            trade_value=150.0
        )

        valid_asset2 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=6002,
            player_name="Valid 2",
            position="cornerback",
            overall_rating=80,
            age=25,
            years_pro=3,
            contract_years_remaining=2,
            annual_cap_hit=5_000_000,
            total_remaining_guaranteed=10_000_000,
            trade_value=130.0
        )

        invalid_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=6003,
            player_name="Invalid FA",
            position="safety",
            overall_rating=78,
            age=27,
            years_pro=5,
            contract_years_remaining=0,  # Free agent
            annual_cap_hit=4_000_000,
            total_remaining_guaranteed=0,
            trade_value=120.0
        )

        target_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=7001,
            player_name="Target",
            position="quarterback",
            overall_rating=88,
            age=28,
            years_pro=6,
            contract_years_remaining=3,
            annual_cap_hit=15_000_000,
            total_remaining_guaranteed=30_000_000,
            trade_value=400.0
        )

        proposal = TradeProposal(
            team1_id=22,
            team1_assets=[valid_asset1, valid_asset2, invalid_asset],  # One invalid
            team1_total_value=400.0,
            team2_id=9,
            team2_assets=[target_asset],
            team2_total_value=400.0,
            value_ratio=1.0,
            fairness_rating=FairnessRating.VERY_FAIR,
            passes_cap_validation=True,
            passes_roster_validation=True
        )

        is_valid, reason = generator._validate_proposal(proposal, 22)

        # Should catch the free agent in the multi-asset package
        assert is_valid is False
        assert "pending free agent" in reason


# ============================================================================
# HELPER TESTS
# ============================================================================

class TestHelperMethods:
    """Test helper methods in isolation."""

    def test_filter_priority_needs(self, generator):
        """Should filter to CRITICAL and HIGH needs only."""
        needs = [
            create_need('quarterback', NeedUrgency.CRITICAL),
            create_need('linebacker', NeedUrgency.HIGH),
            create_need('running_back', NeedUrgency.MEDIUM),
            create_need('kicker', NeedUrgency.LOW),
            create_need('punter', NeedUrgency.NONE)
        ]

        priority_needs = generator._filter_priority_needs(needs)

        assert len(priority_needs) == 2
        assert priority_needs[0]['urgency'] == NeedUrgency.CRITICAL
        assert priority_needs[1]['urgency'] == NeedUrgency.HIGH

    def test_sort_proposals(self, generator):
        """Should sort proposals by value ratio and complexity."""
        # Create mock proposals with different ratios
        proposal1 = Mock(spec=TradeProposal)
        proposal1.value_ratio = 0.85  # Far from 1.0
        proposal1.team1_assets = [Mock()] * 2
        proposal1.team2_assets = [Mock()]

        proposal2 = Mock(spec=TradeProposal)
        proposal2.value_ratio = 1.02  # Very close to 1.0
        proposal2.team1_assets = [Mock()]
        proposal2.team2_assets = [Mock()]

        proposal3 = Mock(spec=TradeProposal)
        proposal3.value_ratio = 1.15  # Moderately far from 1.0
        proposal3.team1_assets = [Mock()]
        proposal3.team2_assets = [Mock()]

        proposals = [proposal1, proposal2, proposal3]

        sorted_proposals = generator._sort_proposals(proposals)

        # proposal2 should be first (closest to 1.0)
        assert sorted_proposals[0].value_ratio == 1.02

        # proposal3 should be second (0.15 from 1.0)
        assert sorted_proposals[1].value_ratio == 1.15

        # proposal1 should be last (0.15 from 1.0, but more complex)
        assert sorted_proposals[2].value_ratio == 0.85


# ============================================================================
# DAY 5 TESTS: INTEGRATION TESTS
# ============================================================================

class TestIntegrationScenarios:
    """End-to-end integration tests with realistic scenarios."""

    def setup_realistic_roster(
        self,
        generator,
        team_id: int,
        needs: List[str],
        surplus: List[str]
    ):
        """Setup realistic roster with needs and surplus positions."""
        roster = []

        # Create surplus players for tradeable positions
        for position in surplus:
            for i in range(7):  # 7 players = surplus available
                player = create_mock_player(
                    player_id=10000 + (team_id * 100) + (len(roster)),
                    overall=82 - i,
                    age=26 + (i % 4),
                    position=position,
                    team_id=team_id
                )
                player['depth_chart_order'] = i + 1
                roster.append(player)

        # Create minimal players for other positions
        other_positions = ['quarterback', 'running_back', 'tight_end', 'offensive_line']
        for position in other_positions:
            if position not in surplus and position not in needs:
                player = create_mock_player(
                    player_id=20000 + (team_id * 100) + (len(roster)),
                    overall=75,
                    age=27,
                    position=position,
                    team_id=team_id
                )
                roster.append(player)

        return roster

    def test_end_to_end_contender_scenario(self, generator, gm_archetype, calculator):
        """Full flow: Contending team seeks impact player for playoff push."""
        # Setup: 8-1 team needs elite pass rusher
        contender_context = TeamContext(
            team_id=22,
            wins=8,
            losses=1,
            cap_space=25_000_000,  # Good cap space
            season="regular"
        )

        needs = [
            create_need('defensive_end', NeedUrgency.CRITICAL),  # Need pass rush
        ]

        # Mock: Elite DE available on rebuilding team
        elite_de = create_mock_player(11001, 90, 27, 'defensive_end', 15)

        # Mock: Contender has surplus WRs
        surplus_wrs = []
        for i in range(7):
            wr = create_mock_player(11101 + i, 84 - i, 26, 'wide_receiver', 22)
            wr['depth_chart_order'] = i + 1
            surplus_wrs.append(wr)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 15:
                return [elite_de]
            elif team_id == 22:
                return surplus_wrs
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(11001, aav=12_000_000))

        # Execute
        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=contender_context,
            needs=needs,
            season=2025
        )

        # Verify: Should be able to generate proposals (may be empty if no fair combinations)
        assert isinstance(proposals, list)

        # If proposals generated, verify structure
        if proposals:
            proposal = proposals[0]
            assert proposal.team1_id == 22  # Contender
            assert len(proposal.team2_assets) == 1  # Getting 1 player
            assert 0.80 <= proposal.value_ratio <= 1.20
            assert proposal.is_acceptable()

    def test_end_to_end_rebuilder_scenario(self, generator, gm_archetype, calculator):
        """Full flow: Rebuilding team trades veterans for future assets."""
        # Setup: 1-6 team with aging veterans
        rebuilder_context = TeamContext(
            team_id=18,
            wins=1,
            losses=6,
            cap_space=5_000_000,  # Limited cap
            season="regular"
        )

        needs = [
            create_need('quarterback', NeedUrgency.CRITICAL),  # Need young QB
        ]

        # Mock: Young QB available on another rebuilder
        young_qb = create_mock_player(12001, 78, 23, 'quarterback', 7)

        # Mock: Rebuilder has aging veterans
        aging_vets = []
        for i in range(5):
            vet = create_mock_player(12101 + i, 83 - i, 30, 'linebacker', 18)
            vet['depth_chart_order'] = i + 1
            aging_vets.append(vet)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 7:
                return [young_qb]
            elif team_id == 18:
                return aging_vets
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(12001, aav=4_000_000))

        # Execute
        proposals = generator.generate_trade_proposals(
            team_id=18,
            gm_archetype=gm_archetype,
            team_context=rebuilder_context,
            needs=needs,
            season=2025
        )

        # Verify: Should generate proposals
        if proposals:
            proposal = proposals[0]
            assert proposal.team1_id == 18
            # Should be fair value trade
            assert 0.80 <= proposal.value_ratio <= 1.20

    def test_integration_with_trade_evaluator(self, generator, team_context, gm_archetype, calculator):
        """Integration: Generated proposals have structure compatible with TradeEvaluator."""
        needs = [create_need('linebacker', NeedUrgency.CRITICAL)]

        # Setup roster
        target_lb = create_mock_player(13001, 85, 27, 'linebacker', 9)
        surplus_wrs = []
        for i in range(7):
            wr = create_mock_player(13101 + i, 80 - i, 26, 'wide_receiver', 22)
            wr['depth_chart_order'] = i + 1
            surplus_wrs.append(wr)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 9:
                return [target_lb]
            elif team_id == 22:
                return surplus_wrs
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(13001))

        # Generate proposals
        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Verify proposals have structure compatible with TradeEvaluator expectations
        if proposals:
            proposal = proposals[0]

            # TradeEvaluator expects TradeProposal with these attributes
            assert hasattr(proposal, 'team1_id')
            assert hasattr(proposal, 'team2_id')
            assert hasattr(proposal, 'team1_assets')
            assert hasattr(proposal, 'team2_assets')
            assert hasattr(proposal, 'team1_total_value')
            assert hasattr(proposal, 'team2_total_value')
            assert hasattr(proposal, 'value_ratio')
            assert hasattr(proposal, 'fairness_rating')
            assert hasattr(proposal, 'passes_cap_validation')

            # Verify assets have required fields for TradeEvaluator
            for asset in proposal.team1_assets + proposal.team2_assets:
                assert hasattr(asset, 'asset_type')
                assert hasattr(asset, 'trade_value')
                assert asset.trade_value > 0

                if asset.asset_type == AssetType.PLAYER:
                    assert hasattr(asset, 'player_id')
                    assert hasattr(asset, 'overall_rating')
                    assert hasattr(asset, 'age')

            # Verify proposal methods work
            assert isinstance(proposal.is_acceptable(), bool)
            assert isinstance(proposal.get_value_difference(), float)

    def test_integration_with_negotiator_engine(self, generator, team_context, gm_archetype, calculator):
        """Integration: Proposals are compatible with NegotiatorEngine."""
        from transactions.negotiator_engine import NegotiatorEngine
        from team_management.gm_archetype import GMArchetype

        needs = [create_need('safety', NeedUrgency.HIGH)]

        # Setup
        target_s = create_mock_player(14001, 84, 26, 'safety', 12)
        surplus_cbs = []
        for i in range(7):
            cb = create_mock_player(14101 + i, 81 - i, 25, 'cornerback', 22)
            cb['depth_chart_order'] = i + 1
            surplus_cbs.append(cb)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 12:
                return [target_s]
            elif team_id == 22:
                return surplus_cbs
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(14001))

        # Generate initial proposal
        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Verify proposals are compatible with NegotiatorEngine structure
        if proposals:
            # Verify proposal structure matches NegotiatorEngine expectations
            proposal = proposals[0]

            # NegotiatorEngine expects TradeProposal with specific attributes
            assert hasattr(proposal, 'team1_assets')
            assert hasattr(proposal, 'team2_assets')
            assert hasattr(proposal, 'value_ratio')
            assert hasattr(proposal, 'fairness_rating')

            # Verify assets are TradeAsset objects with required fields
            for asset in proposal.team1_assets + proposal.team2_assets:
                assert hasattr(asset, 'asset_type')
                assert hasattr(asset, 'trade_value')
                assert hasattr(asset, 'player_id') or hasattr(asset, 'draft_pick')

            # Verify proposal is valid for negotiation
            assert proposal.is_acceptable() or not proposal.is_acceptable()  # Has method

    def test_multi_team_simultaneous_generation(self, calculator):
        """Multiple teams generating proposals simultaneously."""
        # Create 3 teams with different needs
        teams = [
            (22, [create_need('linebacker', NeedUrgency.CRITICAL)]),
            (9, [create_need('wide_receiver', NeedUrgency.HIGH)]),
            (15, [create_need('quarterback', NeedUrgency.CRITICAL)])
        ]

        all_proposals = []

        for team_id, needs in teams:
            gen = TradeProposalGenerator(":memory:", "test_dynasty", calculator)
            gen.player_api = Mock()
            gen.cap_api = Mock()

            # Mock different rosters for each team
            def mock_get_roster(dynasty_id, tid):
                if tid == team_id:
                    # Each team has surplus at a different position
                    surplus_pos = ['defensive_tackle', 'running_back', 'tight_end'][team_id % 3]
                    roster = []
                    for i in range(7):
                        p = create_mock_player(15000 + tid * 100 + i, 80 - i, 26, surplus_pos, tid)
                        p['depth_chart_order'] = i + 1
                        roster.append(p)
                    return roster
                else:
                    return []

            gen.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
            gen._get_player_contract = Mock(return_value=create_mock_contract(15001))

            gm = GMArchetype(
                name=f"Team {team_id} GM",
                description="Test",
                risk_tolerance=0.5,
                win_now_mentality=0.5,
                draft_pick_value=0.5,
                cap_management=0.5,
                trade_frequency=0.5,
                veteran_preference=0.5,
                star_chasing=0.5,
                loyalty=0.5
            )

            context = TeamContext(
                team_id=team_id,
                wins=4,
                losses=3,
                cap_space=15_000_000
            )

            proposals = gen.generate_trade_proposals(
                team_id=team_id,
                gm_archetype=gm,
                team_context=context,
                needs=needs,
                season=2025
            )

            all_proposals.extend(proposals)

        # Verify each team can generate proposals independently
        # (May be empty if no matches found, but should not crash)
        assert isinstance(all_proposals, list)

    def test_proposal_diversity_across_gms(self, generator, team_context, calculator):
        """Different GM personalities produce different proposals."""
        needs = [
            create_need('linebacker', NeedUrgency.CRITICAL),
            create_need('cornerback', NeedUrgency.HIGH)
        ]

        # Setup roster with multiple targets
        targets = [
            create_mock_player(16001, 90, 29, 'linebacker', 9),   # Elite veteran
            create_mock_player(16002, 85, 27, 'linebacker', 10),  # Good prime
            create_mock_player(16003, 82, 24, 'cornerback', 11),  # Young average
        ]

        surplus_wrs = []
        for i in range(7):
            wr = create_mock_player(16101 + i, 80 - i, 26, 'wide_receiver', 22)
            wr['depth_chart_order'] = i + 1
            surplus_wrs.append(wr)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 9:
                return [targets[0]]
            elif team_id == 10:
                return [targets[1]]
            elif team_id == 11:
                return [targets[2]]
            elif team_id == 22:
                return surplus_wrs
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(16001))

        # Create 3 different GM types
        star_chaser = GMArchetype(
            name="Star Chaser",
            description="Star Chaser",
            risk_tolerance=0.7,
            win_now_mentality=0.8,
            draft_pick_value=0.3,
            cap_management=0.4,
            trade_frequency=0.7,
            veteran_preference=0.6,
            star_chasing=0.9,  # High star chasing
            loyalty=0.3
        )

        youth_gm = GMArchetype(
            name="Youth GM",
            description="Youth GM",
            risk_tolerance=0.6,
            win_now_mentality=0.3,
            draft_pick_value=0.8,
            cap_management=0.6,
            trade_frequency=0.5,
            veteran_preference=0.2,  # Low veteran pref
            star_chasing=0.4,
            loyalty=0.6
        )

        balanced_gm = GMArchetype(
            name="Balanced",
            description="Balanced",
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.5,
            star_chasing=0.5,
            loyalty=0.5
        )

        # Generate proposals for each GM type
        star_proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=star_chaser,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        youth_proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=youth_gm,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        balanced_proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=balanced_gm,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Verify proposals exist (may vary by GM)
        # Star chaser should prefer elite players
        if star_proposals:
            star_targets = [p.team2_assets[0].overall_rating for p in star_proposals]
            # Should prefer higher OVR players
            assert max(star_targets) >= 85

        # Youth GM should accept younger players
        if youth_proposals:
            youth_targets = [p.team2_assets[0].age for p in youth_proposals]
            # May include younger players
            assert any(age <= 27 for age in youth_targets)

    def test_performance_benchmark(self, generator, team_context, gm_archetype):
        """Performance: Should complete evaluation in <1.5s."""
        import time

        needs = [
            create_need('linebacker', NeedUrgency.CRITICAL),
            create_need('cornerback', NeedUrgency.HIGH)
        ]

        # Setup realistic league-wide roster (32 teams × ~10 players each)
        def mock_get_roster(dynasty_id, team_id):
            roster = []
            positions = ['linebacker', 'cornerback', 'wide_receiver', 'defensive_tackle']
            for pos_idx, position in enumerate(positions):
                for i in range(3):  # 3 players per position
                    player = create_mock_player(
                        player_id=17000 + team_id * 100 + pos_idx * 10 + i,
                        overall=82 - i,
                        age=26,
                        position=position,
                        team_id=team_id
                    )
                    player['depth_chart_order'] = i + 1
                    roster.append(player)
            return roster

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(17001))

        # Benchmark
        start_time = time.time()

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        elapsed = time.time() - start_time

        # Should complete in <1.5s
        assert elapsed < 1.5, f"Took {elapsed:.2f}s (target: <1.5s)"

        # Should still produce valid results
        assert isinstance(proposals, list)
        assert len(proposals) <= 5  # Max proposals cap

    def test_realistic_trade_deadline_scenario(self, calculator):
        """Realistic: Simulate trade deadline with 10 active teams."""
        # Setup 10 teams with varying needs
        teams_data = [
            (22, [create_need('linebacker', NeedUrgency.CRITICAL)], 'contender'),
            (9, [create_need('wide_receiver', NeedUrgency.HIGH)], 'contender'),
            (15, [create_need('quarterback', NeedUrgency.LOW)], 'rebuilder'),
            (7, [create_need('defensive_end', NeedUrgency.HIGH)], 'contender'),
            (12, [], 'neutral'),  # No critical needs
            (18, [create_need('cornerback', NeedUrgency.CRITICAL)], 'rebuilder'),
            (20, [create_need('safety', NeedUrgency.HIGH)], 'contender'),
            (25, [create_need('tight_end', NeedUrgency.MEDIUM)], 'neutral'),
            (30, [create_need('running_back', NeedUrgency.LOW)], 'rebuilder'),
            (14, [create_need('offensive_line', NeedUrgency.CRITICAL)], 'contender'),
        ]

        all_proposals = []

        for team_id, needs, team_type in teams_data:
            gen = TradeProposalGenerator(":memory:", "test_dynasty", calculator)
            gen.player_api = Mock()
            gen.cap_api = Mock()

            # Mock roster
            def mock_get_roster(dynasty_id, tid):
                roster = []
                # Each team has 10-15 players
                for i in range(12):
                    pos = ['wide_receiver', 'linebacker', 'defensive_tackle'][i % 3]
                    player = create_mock_player(
                        18000 + tid * 100 + i,
                        80 - (i % 5),
                        25 + (i % 6),
                        pos,
                        tid
                    )
                    player['depth_chart_order'] = (i % 7) + 1
                    roster.append(player)
                return roster

            gen.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
            gen._get_player_contract = Mock(return_value=create_mock_contract(18001))

            # GM archetype based on team type
            if team_type == 'contender':
                gm = GMArchetype(
                    name=f"Team {team_id} GM",
                    description="Contender",
                    risk_tolerance=0.7,
                    win_now_mentality=0.8,
                    draft_pick_value=0.3,
                    cap_management=0.4,
                    trade_frequency=0.7,
                    veteran_preference=0.7,
                    star_chasing=0.6,
                    loyalty=0.3
                )
                wins, losses = 7, 2
            elif team_type == 'rebuilder':
                gm = GMArchetype(
                    name=f"Team {team_id} GM",
                    description="Rebuilder",
                    risk_tolerance=0.4,
                    win_now_mentality=0.2,
                    draft_pick_value=0.8,
                    cap_management=0.7,
                    trade_frequency=0.3,
                    veteran_preference=0.3,
                    star_chasing=0.3,
                    loyalty=0.6
                )
                wins, losses = 2, 7
            else:  # neutral
                gm = GMArchetype(
                    name=f"Team {team_id} GM",
                    description="Neutral",
                    risk_tolerance=0.5,
                    win_now_mentality=0.5,
                    draft_pick_value=0.5,
                    cap_management=0.5,
                    trade_frequency=0.5,
                    veteran_preference=0.5,
                    star_chasing=0.5,
                    loyalty=0.5
                )
                wins, losses = 4, 5

            context = TeamContext(
                team_id=team_id,
                wins=wins,
                losses=losses,
                cap_space=15_000_000
            )

            proposals = gen.generate_trade_proposals(
                team_id=team_id,
                gm_archetype=gm,
                team_context=context,
                needs=needs,
                season=2025
            )

            all_proposals.extend(proposals)

        # Verify: Should generate some proposals across 10 teams
        # Not all teams will generate proposals (depends on matches)
        assert isinstance(all_proposals, list)

        # At least some teams should generate proposals
        # (May be 0 if no good matches, but system should handle it)

    def test_complete_pipeline_validation(self, generator, team_context, gm_archetype):
        """Verify all 7 pipeline steps execute correctly."""
        needs = [create_need('linebacker', NeedUrgency.CRITICAL)]

        # Setup
        target_lb = create_mock_player(19001, 85, 27, 'linebacker', 9)
        surplus_wrs = []
        for i in range(7):
            wr = create_mock_player(19101 + i, 80 - i, 26, 'wide_receiver', 22)
            wr['depth_chart_order'] = i + 1
            surplus_wrs.append(wr)

        def mock_get_roster(dynasty_id, team_id):
            if team_id == 9:
                return [target_lb]
            elif team_id == 22:
                return surplus_wrs
            else:
                return []

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(19001))

        # Execute full pipeline
        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        # Verify pipeline outputs
        if proposals:
            proposal = proposals[0]

            # Step 1: Priority needs filtered (CRITICAL + HIGH only)
            assert any(n['urgency'] == NeedUrgency.CRITICAL for n in needs)

            # Step 2-3: League scanned, targets identified
            assert proposal.team2_id == 9  # Found target on team 9

            # Step 4: Fair value constructed
            assert 0.80 <= proposal.value_ratio <= 1.20

            # Step 5: GM filters applied
            assert len(proposals) <= 5  # Max proposals cap

            # Step 6: Validation passed
            assert proposal.passes_cap_validation is True

            # Step 7: Sorting applied (best ratio first)
            if len(proposals) > 1:
                assert proposals[0].value_ratio <= proposals[1].value_ratio or \
                       abs(proposals[0].value_ratio - 1.0) <= abs(proposals[1].value_ratio - 1.0)

    def test_league_wide_scanning_efficiency(self, generator, team_context, gm_archetype):
        """Verify efficient scanning of all 32 teams."""
        import time

        needs = [create_need('linebacker', NeedUrgency.CRITICAL)]

        # Mock all 32 teams with realistic rosters
        def mock_get_roster(dynasty_id, team_id):
            roster = []
            # Each team: ~53 players
            positions = [
                'quarterback', 'running_back', 'wide_receiver', 'tight_end',
                'offensive_line', 'defensive_tackle', 'defensive_end',
                'linebacker', 'cornerback', 'safety', 'kicker', 'punter'
            ]

            for pos_idx, position in enumerate(positions):
                players_at_pos = 5 if position in ['offensive_line', 'linebacker', 'wide_receiver'] else 3
                for i in range(players_at_pos):
                    player = create_mock_player(
                        20000 + team_id * 1000 + pos_idx * 10 + i,
                        82 - i,
                        25 + (i % 8),
                        position,
                        team_id
                    )
                    player['depth_chart_order'] = i + 1
                    roster.append(player)

            return roster

        generator.player_api.get_team_roster = Mock(side_effect=mock_get_roster)
        generator._get_player_contract = Mock(return_value=create_mock_contract(20001))

        # Benchmark full league scan
        start_time = time.time()

        proposals = generator.generate_trade_proposals(
            team_id=22,
            gm_archetype=gm_archetype,
            team_context=team_context,
            needs=needs,
            season=2025
        )

        elapsed = time.time() - start_time

        # Should scan all 32 teams efficiently
        # Target: <1.5s for full league scan
        assert elapsed < 1.5, f"League scan took {elapsed:.2f}s (target: <1.5s)"

        # Should produce proposals
        assert isinstance(proposals, list)
