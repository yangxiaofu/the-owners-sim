"""
Unit tests for GMArchetype dataclass
"""

import pytest
import json
from src.team_management.gm_archetype import GMArchetype


class TestGMArchetype:
    """Test suite for GMArchetype dataclass"""

    def test_valid_archetype_creation(self):
        """Test creating archetype with valid values"""
        archetype = GMArchetype(
            name="Test GM",
            description="Test archetype",
            risk_tolerance=0.5,
            win_now_mentality=0.7
        )
        assert archetype.name == "Test GM"
        assert archetype.risk_tolerance == 0.5
        assert archetype.win_now_mentality == 0.7

    def test_default_values(self):
        """Test that default values are set correctly"""
        archetype = GMArchetype(
            name="Test",
            description="Test desc"
        )
        assert archetype.risk_tolerance == 0.5
        assert archetype.trade_frequency == 0.5
        assert archetype.patience_years == 3

    def test_trait_validation_too_high(self):
        """Test that trait values > 1.0 raise ValueError"""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            GMArchetype(
                name="Invalid",
                description="Test",
                risk_tolerance=1.5
            )

    def test_trait_validation_too_low(self):
        """Test that trait values < 0.0 raise ValueError"""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            GMArchetype(
                name="Invalid",
                description="Test",
                trade_frequency=-0.1
            )

    def test_trait_validation_exactly_zero(self):
        """Test that 0.0 is valid"""
        archetype = GMArchetype(
            name="Valid",
            description="Test",
            risk_tolerance=0.0
        )
        assert archetype.risk_tolerance == 0.0

    def test_trait_validation_exactly_one(self):
        """Test that 1.0 is valid"""
        archetype = GMArchetype(
            name="Valid",
            description="Test",
            risk_tolerance=1.0
        )
        assert archetype.risk_tolerance == 1.0

    def test_patience_years_validation_too_low(self):
        """Test that patience_years < 1 raises ValueError"""
        with pytest.raises(ValueError, match="patience_years must be between"):
            GMArchetype(
                name="Invalid",
                description="Test",
                patience_years=0
            )

    def test_patience_years_validation_too_high(self):
        """Test that patience_years > 10 raises ValueError"""
        with pytest.raises(ValueError, match="patience_years must be between"):
            GMArchetype(
                name="Invalid",
                description="Test",
                patience_years=15
            )

    def test_patience_years_valid_range(self):
        """Test valid patience_years values"""
        for years in [1, 5, 10]:
            archetype = GMArchetype(
                name="Valid",
                description="Test",
                patience_years=years
            )
            assert archetype.patience_years == years

    def test_to_dict(self):
        """Test converting archetype to dictionary"""
        archetype = GMArchetype(
            name="Test",
            description="Test desc",
            risk_tolerance=0.6,
            trade_frequency=0.7
        )
        data = archetype.to_dict()

        assert data['name'] == "Test"
        assert data['description'] == "Test desc"
        assert data['risk_tolerance'] == 0.6
        assert data['trade_frequency'] == 0.7
        assert 'win_now_mentality' in data
        assert 'patience_years' in data

    def test_from_dict(self):
        """Test creating archetype from dictionary"""
        data = {
            'name': "Test",
            'description': "Test desc",
            'risk_tolerance': 0.7,
            'win_now_mentality': 0.5,
            'draft_pick_value': 0.5,
            'cap_management': 0.5,
            'trade_frequency': 0.5,
            'veteran_preference': 0.5,
            'star_chasing': 0.3,
            'loyalty': 0.5,
            'desperation_threshold': 0.7,
            'patience_years': 3,
            'deadline_activity': 0.5,
            'premium_position_focus': 0.6
        }
        archetype = GMArchetype.from_dict(data)

        assert archetype.name == "Test"
        assert archetype.risk_tolerance == 0.7
        assert archetype.win_now_mentality == 0.5

    def test_to_json(self):
        """Test JSON serialization"""
        archetype = GMArchetype(
            name="Test",
            description="Test desc",
            risk_tolerance=0.8
        )

        json_str = archetype.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data['name'] == "Test"
        assert data['risk_tolerance'] == 0.8

    def test_from_json(self):
        """Test creating from JSON string"""
        json_str = '''
        {
            "name": "Test",
            "description": "Test desc",
            "risk_tolerance": 0.9,
            "win_now_mentality": 0.5,
            "draft_pick_value": 0.5,
            "cap_management": 0.5,
            "trade_frequency": 0.5,
            "veteran_preference": 0.5,
            "star_chasing": 0.3,
            "loyalty": 0.5,
            "desperation_threshold": 0.7,
            "patience_years": 3,
            "deadline_activity": 0.5,
            "premium_position_focus": 0.6
        }
        '''

        archetype = GMArchetype.from_json(json_str)
        assert archetype.name == "Test"
        assert archetype.risk_tolerance == 0.9

    def test_json_roundtrip(self):
        """Test JSON serialization round-trip"""
        original = GMArchetype(
            name="Test",
            description="Test desc",
            risk_tolerance=0.8,
            trade_frequency=0.6
        )

        json_str = original.to_json()
        restored = GMArchetype.from_json(json_str)

        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.risk_tolerance == original.risk_tolerance
        assert restored.trade_frequency == original.trade_frequency

    def test_apply_customizations(self):
        """Test applying customizations to archetype"""
        base = GMArchetype(
            name="Base",
            description="Base archetype",
            risk_tolerance=0.5,
            trade_frequency=0.5
        )

        customized = base.apply_customizations({
            'risk_tolerance': 0.7,
            'name': "Customized"
        })

        # Original unchanged
        assert base.risk_tolerance == 0.5
        assert base.name == "Base"

        # Customized has new values
        assert customized.risk_tolerance == 0.7
        assert customized.name == "Customized"
        assert customized.trade_frequency == 0.5  # Unchanged trait

    def test_apply_customizations_validation(self):
        """Test that customizations are still validated"""
        base = GMArchetype(
            name="Base",
            description="Base archetype"
        )

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            base.apply_customizations({'risk_tolerance': 1.5})

    def test_all_traits_present(self):
        """Test that all expected traits are present"""
        archetype = GMArchetype(
            name="Test",
            description="Test"
        )

        expected_traits = [
            'name', 'description', 'risk_tolerance', 'win_now_mentality',
            'draft_pick_value', 'cap_management', 'trade_frequency',
            'veteran_preference', 'star_chasing', 'loyalty',
            'desperation_threshold', 'patience_years', 'deadline_activity',
            'premium_position_focus'
        ]

        for trait in expected_traits:
            assert hasattr(archetype, trait), f"Missing trait: {trait}"

    def test_extreme_values(self):
        """Test archetypes with extreme values"""
        # Very aggressive archetype
        aggressive = GMArchetype(
            name="Ultra Aggressive",
            description="Test",
            risk_tolerance=1.0,
            win_now_mentality=1.0,
            trade_frequency=1.0,
            star_chasing=1.0,
            patience_years=1
        )
        assert aggressive.risk_tolerance == 1.0

        # Very conservative archetype
        conservative = GMArchetype(
            name="Ultra Conservative",
            description="Test",
            risk_tolerance=0.0,
            win_now_mentality=0.0,
            trade_frequency=0.0,
            star_chasing=0.0,
            patience_years=10
        )
        assert conservative.risk_tolerance == 0.0
