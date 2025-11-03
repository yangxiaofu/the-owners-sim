"""
Unit tests for GMArchetypeFactory
"""

import pytest
from pathlib import Path
from src.team_management.gm_archetype_factory import GMArchetypeFactory
from src.team_management.gm_archetype import GMArchetype


class TestGMArchetypeFactory:
    """Test suite for GMArchetypeFactory"""

    @pytest.fixture
    def factory(self):
        """Create factory instance for testing"""
        return GMArchetypeFactory()

    def test_factory_initialization(self, factory):
        """Test factory initializes and loads base archetypes"""
        assert len(factory._base_archetypes) == 7
        assert 'win_now' in factory._base_archetypes
        assert 'rebuilder' in factory._base_archetypes
        assert 'balanced' in factory._base_archetypes
        assert 'aggressive_trader' in factory._base_archetypes
        assert 'conservative' in factory._base_archetypes
        assert 'draft_hoarder' in factory._base_archetypes
        assert 'star_chaser' in factory._base_archetypes

    def test_base_archetypes_are_gm_archetype_instances(self, factory):
        """Test that loaded base archetypes are GMArchetype instances"""
        for archetype in factory._base_archetypes.values():
            assert isinstance(archetype, GMArchetype)

    def test_get_base_archetype_success(self, factory):
        """Test retrieving valid base archetype"""
        archetype = factory.get_base_archetype('win_now')

        assert archetype.name == "Win-Now"
        assert archetype.win_now_mentality > 0.7
        assert archetype.draft_pick_value < 0.4

    def test_get_base_archetype_rebuilder(self, factory):
        """Test rebuilder archetype has correct traits"""
        archetype = factory.get_base_archetype('rebuilder')

        assert archetype.name == "Rebuilder"
        assert archetype.draft_pick_value > 0.7
        assert archetype.win_now_mentality < 0.3

    def test_get_base_archetype_balanced(self, factory):
        """Test balanced archetype has moderate traits"""
        archetype = factory.get_base_archetype('balanced')

        assert archetype.name == "Balanced"
        assert 0.4 <= archetype.risk_tolerance <= 0.6
        assert 0.4 <= archetype.win_now_mentality <= 0.6

    def test_get_base_archetype_invalid(self, factory):
        """Test retrieving invalid archetype raises ValueError"""
        with pytest.raises(ValueError, match="Unknown archetype"):
            factory.get_base_archetype('nonexistent')

    def test_get_team_archetype_valid(self, factory):
        """Test retrieving team archetype by ID"""
        # Chiefs (team 15) should be Win-Now
        archetype = factory.get_team_archetype(15)

        assert isinstance(archetype, GMArchetype)
        assert archetype.name == "Win-Now"

    def test_get_team_archetype_invalid_id_too_low(self, factory):
        """Test invalid team ID (too low) raises ValueError"""
        with pytest.raises(ValueError, match="team_id must be between"):
            factory.get_team_archetype(0)

    def test_get_team_archetype_invalid_id_too_high(self, factory):
        """Test invalid team ID (too high) raises ValueError"""
        with pytest.raises(ValueError, match="team_id must be between"):
            factory.get_team_archetype(50)

    def test_team_archetype_caching(self, factory):
        """Test that team archetypes are cached"""
        archetype1 = factory.get_team_archetype(15)
        archetype2 = factory.get_team_archetype(15)

        # Should be same object (cached)
        assert archetype1 is archetype2

    def test_clear_cache(self, factory):
        """Test cache clearing"""
        factory.get_team_archetype(15)
        assert 15 in factory._team_archetypes

        factory.clear_cache()
        assert 15 not in factory._team_archetypes

    def test_reload_team_archetype(self, factory):
        """Test reloading archetype bypasses cache"""
        archetype1 = factory.get_team_archetype(15)
        archetype2 = factory.reload_team_archetype(15)

        # Should be different objects
        assert archetype1 is not archetype2
        # But same values
        assert archetype1.name == archetype2.name
        assert archetype1.win_now_mentality == archetype2.win_now_mentality

    def test_get_all_team_archetypes(self, factory):
        """Test getting all 32 team archetypes"""
        all_archetypes = factory.get_all_team_archetypes()

        assert len(all_archetypes) == 32
        assert all(1 <= team_id <= 32 for team_id in all_archetypes.keys())
        assert all(isinstance(arch, GMArchetype) for arch in all_archetypes.values())

    def test_archetype_diversity(self, factory):
        """Test that teams have diverse archetypes"""
        all_archetypes = factory.get_all_team_archetypes()

        # Collect all risk_tolerance values
        risk_values = [arch.risk_tolerance for arch in all_archetypes.values()]

        # Should have variety (not all the same)
        assert len(set(risk_values)) > 5, "Not enough diversity in risk_tolerance"
        assert min(risk_values) < 0.4, "No low risk_tolerance teams"
        assert max(risk_values) > 0.6, "No high risk_tolerance teams"

    def test_specific_team_assignments(self, factory):
        """Test specific team archetype assignments"""
        # Chiefs (15) - Win-Now
        chiefs = factory.get_team_archetype(15)
        assert chiefs.name == "Win-Now"

        # Bears (5) - Rebuilder
        bears = factory.get_team_archetype(5)
        assert bears.name == "Rebuilder"

        # Rams (17) - Aggressive Trader
        rams = factory.get_team_archetype(17)
        assert rams.name == "Aggressive Trader"

        # Saints (20) - Conservative
        saints = factory.get_team_archetype(20)
        assert saints.name == "Conservative"

        # Cowboys (10) - Star Chaser
        cowboys = factory.get_team_archetype(10)
        assert cowboys.name == "Star Chaser"

    def test_team_customizations_applied(self, factory):
        """Test that team customizations are applied correctly"""
        # Chiefs have trade_frequency customization in their config
        chiefs = factory.get_team_archetype(15)

        # Should have customized value, not base Win-Now value
        # Chiefs config has trade_frequency: 0.7
        assert chiefs.trade_frequency == 0.7

    def test_team_without_customizations(self, factory):
        """Test teams without customizations use base archetype"""
        # Cardinals (1) - Balanced with no customizations
        cardinals = factory.get_team_archetype(1)

        base_balanced = factory.get_base_archetype('balanced')

        # Should match base archetype exactly
        assert cardinals.risk_tolerance == base_balanced.risk_tolerance
        assert cardinals.trade_frequency == base_balanced.trade_frequency

    def test_all_teams_load_successfully(self, factory):
        """Test that all 32 teams can be loaded without errors"""
        for team_id in range(1, 33):
            archetype = factory.get_team_archetype(team_id)
            assert isinstance(archetype, GMArchetype)
            assert archetype.name is not None
            assert len(archetype.description) > 0

    def test_base_archetypes_have_correct_traits(self, factory):
        """Test base archetypes have appropriate trait values"""
        # Win-Now should have high win_now_mentality, low draft_pick_value
        win_now = factory.get_base_archetype('win_now')
        assert win_now.win_now_mentality > 0.7
        assert win_now.draft_pick_value < 0.4

        # Rebuilder should have opposite
        rebuilder = factory.get_base_archetype('rebuilder')
        assert rebuilder.win_now_mentality < 0.3
        assert rebuilder.draft_pick_value > 0.7

        # Draft Hoarder should have very high draft_pick_value
        draft_hoarder = factory.get_base_archetype('draft_hoarder')
        assert draft_hoarder.draft_pick_value > 0.9

        # Star Chaser should have high star_chasing
        star_chaser = factory.get_base_archetype('star_chaser')
        assert star_chaser.star_chasing > 0.8

        # Aggressive Trader should have high trade_frequency
        aggressive_trader = factory.get_base_archetype('aggressive_trader')
        assert aggressive_trader.trade_frequency > 0.8

        # Conservative should have low trade_frequency, high cap_management
        conservative = factory.get_base_archetype('conservative')
        assert conservative.trade_frequency < 0.3
        assert conservative.cap_management > 0.8

    def test_factory_with_custom_config_path(self):
        """Test factory can be initialized with custom config path"""
        # This should work with default path
        factory = GMArchetypeFactory()
        assert factory.config_path is not None
        assert factory.base_archetypes_path.exists()

    def test_archetype_names_match_descriptions(self, factory):
        """Test that archetype names and descriptions make sense"""
        for key, archetype in factory._base_archetypes.items():
            # Name should be title case version of key
            expected_name = key.replace('_', ' ').title()
            if key == "aggressive_trader":
                expected_name = "Aggressive Trader"
            elif key == "win_now":
                expected_name = "Win-Now"
            elif key == "star_chaser":
                expected_name = "Star Chaser"
            elif key == "draft_hoarder":
                expected_name = "Draft Hoarder"

            assert archetype.name == expected_name
            assert len(archetype.description) > 20  # Should have meaningful description

    def test_cache_independence(self, factory):
        """Test that cache works independently for different teams"""
        chiefs = factory.get_team_archetype(15)
        bears = factory.get_team_archetype(5)

        # Both should be cached
        assert 15 in factory._team_archetypes
        assert 5 in factory._team_archetypes

        # Should be different objects
        assert chiefs is not bears
        assert chiefs.name != bears.name
