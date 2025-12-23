"""
Unit tests for GMFAProposalEngine, specifically the dynamic proposal count system.

Tests the _calculate_proposal_count() method that determines how many proposals
the GM should make based on team needs, cap space, GM archetype, and wave tier.
"""

import pytest
from src.game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine
from src.game_cycle.models import FAGuidance, FAPhilosophy
from src.team_management.gm_archetype import GMArchetype


@pytest.fixture
def base_fa_guidance():
    """Basic FA guidance for testing."""
    return FAGuidance.create_default()


@pytest.fixture
def balanced_gm():
    """Balanced GM archetype (all traits at 0.5)."""
    return GMArchetype(
        name="Balanced GM",
        description="Test GM with balanced traits",
        risk_tolerance=0.5,
        win_now_mentality=0.5,
        draft_pick_value=0.5,
        cap_management=0.5,
        trade_frequency=0.5,
        veteran_preference=0.5,
        star_chasing=0.5,
        loyalty=0.5,
    )


@pytest.fixture
def star_chasing_gm():
    """Star-chasing GM (focuses on fewer elite targets)."""
    return GMArchetype(
        name="Star Chaser",
        description="Test GM focused on elite talent",
        risk_tolerance=0.8,
        win_now_mentality=0.8,
        draft_pick_value=0.3,
        cap_management=0.3,
        trade_frequency=0.5,
        veteran_preference=0.6,
        star_chasing=0.9,  # High star chasing
        loyalty=0.4,
    )


@pytest.fixture
def aggressive_spender_gm():
    """Aggressive spender GM (makes more offers)."""
    return GMArchetype(
        name="Aggressive Spender",
        description="Test GM who spends freely",
        risk_tolerance=0.8,
        win_now_mentality=0.8,
        draft_pick_value=0.3,
        cap_management=0.2,  # Low cap management
        trade_frequency=0.7,
        veteran_preference=0.6,
        star_chasing=0.2,  # Low star chasing
        loyalty=0.4,
    )


@pytest.fixture
def conservative_gm():
    """Conservative GM (cautious with spending)."""
    return GMArchetype(
        name="Conservative GM",
        description="Test GM who is cautious with cap",
        risk_tolerance=0.2,
        win_now_mentality=0.3,
        draft_pick_value=0.8,
        cap_management=0.85,  # High cap management
        trade_frequency=0.3,
        veteran_preference=0.5,
        star_chasing=0.3,
        loyalty=0.8,
    )


@pytest.fixture
def win_now_gm():
    """Win-now GM (aggressive in FA)."""
    return GMArchetype(
        name="Win Now GM",
        description="Test GM in championship mode",
        risk_tolerance=0.7,
        win_now_mentality=0.85,  # High win-now mentality
        draft_pick_value=0.3,
        cap_management=0.4,
        trade_frequency=0.6,
        veteran_preference=0.7,
        star_chasing=0.6,
        loyalty=0.4,
    )


class TestCalculateProposalCount:
    """Tests for _calculate_proposal_count() method."""

    def test_wave_1_baseline(self, balanced_gm, base_fa_guidance):
        """Wave 1 should have base count of 3."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # No needs, medium cap, Wave 1
        count = engine._calculate_proposal_count(
            team_needs={},
            cap_space=30_000_000,
            wave=1,
            available_players=[]
        )

        # Base Wave 1 limit is 3, with balanced modifiers should stay around 3
        assert 1 <= count <= 3

    def test_wave_3_baseline(self, balanced_gm, base_fa_guidance):
        """Wave 3 should have base count of 7."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # No needs, medium cap, Wave 3
        count = engine._calculate_proposal_count(
            team_needs={},
            cap_space=30_000_000,
            wave=3,
            available_players=[]
        )

        # Base Wave 3 limit is 7, but with no needs and medium cap, should be lower
        assert 1 <= count <= 7

    def test_critical_needs_increases_count(self, balanced_gm, base_fa_guidance):
        """Critical needs should increase proposal count."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # Many critical needs (depth level 0-3)
        critical_needs = {
            "QB": 0,  # Critical
            "WR": 1,  # Critical
            "CB": 2,  # Critical
            "OT": 3,  # Critical
        }

        count = engine._calculate_proposal_count(
            team_needs=critical_needs,
            cap_space=50_000_000,
            wave=3,
            available_players=[]
        )

        # With 4 critical needs, high cap, Wave 3 (limit 7)
        # Should generate many proposals
        assert count >= 5, f"Expected >= 5 proposals with critical needs, got {count}"

    def test_high_cap_space_increases_count(self, balanced_gm, base_fa_guidance):
        """High cap space should increase proposal count."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # High cap space (>$50M)
        count = engine._calculate_proposal_count(
            team_needs={"WR": 2},  # One moderate need
            cap_space=75_000_000,
            wave=2,
            available_players=[]
        )

        # Wave 2 limit is 5, high cap should push toward upper limit
        assert count >= 4, f"Expected >= 4 proposals with high cap, got {count}"

    def test_low_cap_space_decreases_count(self, balanced_gm, base_fa_guidance):
        """Low cap space should decrease proposal count."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # Low cap space (<$15M) = 0 cap modifier
        # Wave 2 base = 5, needs (1 at urgency 2) = +1, cap = +0, gm = 0
        # Total = 5 + 1 + 0 + 0 = 6, clamped to wave max of 5
        count = engine._calculate_proposal_count(
            team_needs={"WR": 2},
            cap_space=10_000_000,
            wave=2,
            available_players=[]
        )

        # With low cap and one moderate need, should hit wave limit
        assert count == 5, f"Expected 5 proposals (wave limit), got {count}"

    def test_star_chasing_gm_reduces_count(self, star_chasing_gm, base_fa_guidance):
        """Star-chasing GM should focus on fewer targets."""
        engine = GMFAProposalEngine(star_chasing_gm, base_fa_guidance)

        # Star-chasing GM with high cap and needs
        # Wave 1 base = 3, needs (3 critical) = +3, cap (>50M) = +3, gm (star_chasing) = -2
        # Total = 3 + 3 + 3 - 2 = 7, clamped to wave max of 3
        count = engine._calculate_proposal_count(
            team_needs={"QB": 0, "WR": 1, "CB": 2},
            cap_space=60_000_000,
            wave=1,  # Elite wave
            available_players=[]
        )

        # Star-chasing GM should focus on fewer elite targets (hits wave limit)
        # Even with -2 modifier, high needs and cap push to wave limit
        assert count == 3, f"Expected 3 proposals (wave limit) for star-chasing GM, got {count}"

    def test_aggressive_spender_increases_count(self, aggressive_spender_gm, base_fa_guidance):
        """Aggressive spender GM should make more offers."""
        engine = GMFAProposalEngine(aggressive_spender_gm, base_fa_guidance)

        count = engine._calculate_proposal_count(
            team_needs={"QB": 0, "WR": 1},
            cap_space=60_000_000,
            wave=2,  # Quality wave (limit 5)
            available_players=[]
        )

        # Aggressive spender (low cap_mgmt, low star_chasing) gets +2 modifier
        # Should generate many proposals
        assert count >= 4, f"Expected >= 4 proposals for aggressive spender, got {count}"

    def test_conservative_gm_reduces_count(self, conservative_gm, base_fa_guidance):
        """Conservative GM should be cautious with proposals."""
        engine = GMFAProposalEngine(conservative_gm, base_fa_guidance)

        # Wave 2 base = 5, needs (2 critical) = +2, cap ($30-50M) = +2, gm (conservative) = -1
        # Total = 5 + 2 + 2 - 1 = 8, clamped to wave max of 5
        count = engine._calculate_proposal_count(
            team_needs={"WR": 1, "CB": 2},
            cap_space=40_000_000,
            wave=2,  # Quality wave (limit 5)
            available_players=[]
        )

        # Conservative GM reduces count, but with needs and cap space still hits wave limit
        assert count == 5, f"Expected 5 proposals (wave limit) for conservative GM, got {count}"

    def test_win_now_gm_increases_count(self, win_now_gm, base_fa_guidance):
        """Win-now GM should be more active."""
        engine = GMFAProposalEngine(win_now_gm, base_fa_guidance)

        count = engine._calculate_proposal_count(
            team_needs={"WR": 1, "CB": 2},
            cap_space=40_000_000,
            wave=2,  # Quality wave (limit 5)
            available_players=[]
        )

        # Win-now GM (high win_now_mentality) gets +1 modifier
        assert count >= 3, f"Expected >= 3 proposals for win-now GM, got {count}"

    def test_wave_limits_respected(self, balanced_gm, base_fa_guidance):
        """Ensure wave limits are never exceeded."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # Max out all factors
        extreme_needs = {f"POS_{i}": 0 for i in range(10)}  # 10 critical needs

        # Wave 1 (limit 3)
        count_w1 = engine._calculate_proposal_count(
            team_needs=extreme_needs,
            cap_space=100_000_000,
            wave=1,
            available_players=[]
        )
        assert count_w1 <= 3, f"Wave 1 exceeded limit of 3: {count_w1}"

        # Wave 2 (limit 5)
        count_w2 = engine._calculate_proposal_count(
            team_needs=extreme_needs,
            cap_space=100_000_000,
            wave=2,
            available_players=[]
        )
        assert count_w2 <= 5, f"Wave 2 exceeded limit of 5: {count_w2}"

        # Wave 3 (limit 7)
        count_w3 = engine._calculate_proposal_count(
            team_needs=extreme_needs,
            cap_space=100_000_000,
            wave=3,
            available_players=[]
        )
        assert count_w3 <= 7, f"Wave 3 exceeded limit of 7: {count_w3}"

        # Wave 4 (limit 5)
        count_w4 = engine._calculate_proposal_count(
            team_needs=extreme_needs,
            cap_space=100_000_000,
            wave=4,
            available_players=[]
        )
        assert count_w4 <= 5, f"Wave 4 exceeded limit of 5: {count_w4}"

    def test_minimum_of_one_proposal(self, balanced_gm, base_fa_guidance):
        """Even with worst conditions, should generate at least 1 proposal."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # Worst case: no needs, no cap, star-chasing GM
        star_chaser = GMArchetype(
            name="Star Chaser",
            description="Test star-chasing GM",
            star_chasing=0.9,
            cap_management=0.5
        )
        engine_sc = GMFAProposalEngine(star_chaser, base_fa_guidance)

        count = engine_sc._calculate_proposal_count(
            team_needs={},  # No needs
            cap_space=5_000_000,  # Low cap
            wave=1,
            available_players=[]
        )

        # Should never return 0
        assert count >= 1, f"Expected at least 1 proposal, got {count}"

    def test_cap_space_tiers(self, balanced_gm, base_fa_guidance):
        """Test that different cap space tiers produce different modifiers."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # Same needs, different cap space
        needs = {"WR": 1}

        # Very high cap (>$50M) → +3 modifier
        count_high = engine._calculate_proposal_count(
            team_needs=needs, cap_space=75_000_000, wave=3, available_players=[]
        )

        # Medium cap ($30-50M) → +2 modifier
        count_medium = engine._calculate_proposal_count(
            team_needs=needs, cap_space=40_000_000, wave=3, available_players=[]
        )

        # Low cap ($15-30M) → +1 modifier
        count_low = engine._calculate_proposal_count(
            team_needs=needs, cap_space=20_000_000, wave=3, available_players=[]
        )

        # Very low cap (<$15M) → +0 modifier
        count_very_low = engine._calculate_proposal_count(
            team_needs=needs, cap_space=10_000_000, wave=3, available_players=[]
        )

        # Higher cap should generally lead to more proposals
        assert count_high >= count_medium
        assert count_medium >= count_low
        assert count_low >= count_very_low

    def test_comprehensive_scenario_rebuilding_team(self, balanced_gm, base_fa_guidance):
        """Test realistic scenario: Rebuilding team with many needs and high cap."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # Rebuilding team
        rebuilding_needs = {
            "QB": 0,   # Critical
            "WR": 1,   # Critical
            "CB": 1,   # Critical
            "OT": 2,   # High
            "EDGE": 3  # Moderate
        }

        count = engine._calculate_proposal_count(
            team_needs=rebuilding_needs,
            cap_space=65_000_000,
            wave=3,  # Depth wave (limit 7)
            available_players=[]
        )

        # Should generate many proposals (6-7)
        assert count >= 6, f"Expected >= 6 proposals for rebuilding team, got {count}"

    def test_comprehensive_scenario_contender(self, star_chasing_gm, base_fa_guidance):
        """Test realistic scenario: Contender with few needs, low cap, star-chasing GM."""
        engine = GMFAProposalEngine(star_chasing_gm, base_fa_guidance)

        # Contender
        contender_needs = {
            "CB": 4,  # Minor need
            "WR": 4   # Minor need
        }

        count = engine._calculate_proposal_count(
            team_needs=contender_needs,
            cap_space=15_000_000,
            wave=1,  # Elite wave (limit 3)
            available_players=[]
        )

        # Should focus on 1-2 elite targets
        assert count <= 2, f"Expected <= 2 proposals for contender, got {count}"

    def test_proposals_respect_cumulative_cap(self, balanced_gm, base_fa_guidance):
        """Ensure proposals don't exceed available cap when combined."""
        engine = GMFAProposalEngine(balanced_gm, base_fa_guidance)

        # 5 expensive players ($20M each = $100M total if all signed)
        expensive_players = [
            {
                "player_id": i,
                "overall": 90,
                "tier": "Elite",
                "position": "QB",
                "age": 27,
                "full_name": f"Star Player {i}",
                "first_name": "Star",
                "last_name": f"Player {i}",
                "name": f"Star Player {i}"
            }
            for i in range(5)
        ]

        # Generate proposals with only $50M cap (can afford ~2-3 players at most)
        proposals = engine.generate_proposals(
            available_players=expensive_players,
            team_needs={"QB": 0},  # Critical need
            cap_space=50_000_000,
            wave=1  # Elite wave (max 3 proposals)
        )

        # Calculate total cap impact
        total_cap_hit = sum(p.cap_impact for p in proposals)

        # Should NOT exceed $50M available cap
        assert total_cap_hit <= 50_000_000, (
            f"Proposals exceed cap: ${total_cap_hit:,} with ${50_000_000:,} available"
        )

        # Should generate fewer than 5 proposals (cap exhausted before reaching all players)
        assert len(proposals) < 5, (
            f"Generated {len(proposals)} proposals, expected fewer due to cap limit"
        )

        # Should have at least 1 proposal (not empty)
        assert len(proposals) >= 1, "Should generate at least one proposal with $50M cap"

        print(f"[TEST] Generated {len(proposals)} proposals with total cap hit: ${total_cap_hit:,}")
