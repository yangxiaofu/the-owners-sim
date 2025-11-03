# Phase 1.1: GM Archetype System - Detailed Implementation Plan

## Overview
Create a complete GM archetype system that defines General Manager personalities and philosophies for all 32 NFL teams. This system will drive AI transaction decisions throughout Phase 1 (trades), Phase 2 (waivers), and Phase 3 (emergency signings).

---

## File Structure

```
src/team_management/
├── gm_archetype.py              # Core GMArchetype dataclass
└── gm_archetype_factory.py      # Factory for loading archetypes

src/config/
├── gm_archetypes/
│   └── base_archetypes.json     # 7 template definitions
└── gm_profiles/
    ├── team_01_arizona_cardinals.json
    ├── team_02_atlanta_falcons.json
    ├── ...
    └── team_32_washington_commanders.json

tests/team_management/
├── test_gm_archetype.py         # Unit tests for GMArchetype
└── test_gm_archetype_factory.py # Factory tests
```

---

## Step 1: Core GMArchetype Dataclass

**File**: `src/team_management/gm_archetype.py`

### Class Definition

```python
from dataclasses import dataclass, field
from typing import Dict, Any
import json

@dataclass
class GMArchetype:
    """
    Defines a General Manager's personality and decision-making philosophy.

    All trait values use 0.0-1.0 continuous scales:
    - 0.0-0.3: Low/Weak tendency
    - 0.3-0.7: Moderate/Balanced
    - 0.7-1.0: High/Strong tendency
    """

    # Identification
    name: str
    description: str

    # Core Personality Traits (0.0-1.0)
    risk_tolerance: float = 0.5
    """Willingness to take gambles on unproven players or risky trades"""

    win_now_mentality: float = 0.5
    """Championship urgency (low = rebuild focus, high = win immediately)"""

    draft_pick_value: float = 0.5
    """How much GM values draft picks vs proven players"""

    cap_management: float = 0.5
    """Financial discipline (low = spends freely, high = conservative with cap)"""

    trade_frequency: float = 0.5
    """Base likelihood of making trades"""

    veteran_preference: float = 0.5
    """Youth focus (low) vs veteran focus (high)"""

    star_chasing: float = 0.3
    """Tendency to pursue superstar players vs balanced roster building"""

    loyalty: float = 0.5
    """Tendency to keep existing players vs turnover"""

    # Situational Modifiers (0.0-1.0)
    desperation_threshold: float = 0.7
    """Performance level (win %) that triggers desperate moves"""

    patience_years: int = 3
    """Number of years willing to commit to rebuild before pivoting"""

    deadline_activity: float = 0.5
    """Trade deadline aggressiveness (relative to normal trade_frequency)"""

    # Position Philosophy (0.0-1.0)
    premium_position_focus: float = 0.6
    """Prioritization of QB/Edge/OT over other positions"""

    def __post_init__(self):
        """Validate all trait values are within acceptable ranges"""
        self._validate_traits()

    def _validate_traits(self):
        """Ensure all float traits are between 0.0 and 1.0"""
        float_traits = [
            'risk_tolerance', 'win_now_mentality', 'draft_pick_value',
            'cap_management', 'trade_frequency', 'veteran_preference',
            'star_chasing', 'loyalty', 'desperation_threshold',
            'deadline_activity', 'premium_position_focus'
        ]

        for trait_name in float_traits:
            value = getattr(self, trait_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{trait_name} must be between 0.0 and 1.0, got {value}"
                )

        # Validate patience_years
        if not 1 <= self.patience_years <= 10:
            raise ValueError(
                f"patience_years must be between 1 and 10, got {self.patience_years}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert archetype to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'risk_tolerance': self.risk_tolerance,
            'win_now_mentality': self.win_now_mentality,
            'draft_pick_value': self.draft_pick_value,
            'cap_management': self.cap_management,
            'trade_frequency': self.trade_frequency,
            'veteran_preference': self.veteran_preference,
            'star_chasing': self.star_chasing,
            'loyalty': self.loyalty,
            'desperation_threshold': self.desperation_threshold,
            'patience_years': self.patience_years,
            'deadline_activity': self.deadline_activity,
            'premium_position_focus': self.premium_position_focus
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GMArchetype':
        """Create archetype from dictionary"""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'GMArchetype':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def apply_customizations(self, customizations: Dict[str, Any]) -> 'GMArchetype':
        """
        Create a new archetype with customized trait values.

        Args:
            customizations: Dict of trait names to new values

        Returns:
            New GMArchetype instance with updated traits
        """
        archetype_dict = self.to_dict()
        archetype_dict.update(customizations)
        return GMArchetype.from_dict(archetype_dict)
```

---

## Step 2: Base Archetype Templates

**File**: `src/config/gm_archetypes/base_archetypes.json`

### Template Definitions

```json
{
  "win_now": {
    "name": "Win-Now",
    "description": "Aggressive GM focused on immediate championship contention, willing to sacrifice future assets",
    "risk_tolerance": 0.7,
    "win_now_mentality": 0.85,
    "draft_pick_value": 0.3,
    "cap_management": 0.4,
    "trade_frequency": 0.65,
    "veteran_preference": 0.75,
    "star_chasing": 0.7,
    "loyalty": 0.4,
    "desperation_threshold": 0.65,
    "patience_years": 2,
    "deadline_activity": 0.8,
    "premium_position_focus": 0.7
  },

  "rebuilder": {
    "name": "Rebuilder",
    "description": "Patient GM focused on long-term success through draft and development",
    "risk_tolerance": 0.35,
    "win_now_mentality": 0.2,
    "draft_pick_value": 0.85,
    "cap_management": 0.7,
    "trade_frequency": 0.4,
    "veteran_preference": 0.3,
    "star_chasing": 0.2,
    "loyalty": 0.6,
    "desperation_threshold": 0.8,
    "patience_years": 5,
    "deadline_activity": 0.3,
    "premium_position_focus": 0.8
  },

  "balanced": {
    "name": "Balanced",
    "description": "Steady, methodical GM who balances short and long-term thinking",
    "risk_tolerance": 0.5,
    "win_now_mentality": 0.5,
    "draft_pick_value": 0.5,
    "cap_management": 0.55,
    "trade_frequency": 0.5,
    "veteran_preference": 0.5,
    "star_chasing": 0.35,
    "loyalty": 0.5,
    "desperation_threshold": 0.7,
    "patience_years": 3,
    "deadline_activity": 0.5,
    "premium_position_focus": 0.6
  },

  "aggressive_trader": {
    "name": "Aggressive Trader",
    "description": "Highly active GM who frequently makes moves to improve roster",
    "risk_tolerance": 0.75,
    "win_now_mentality": 0.6,
    "draft_pick_value": 0.45,
    "cap_management": 0.5,
    "trade_frequency": 0.85,
    "veteran_preference": 0.55,
    "star_chasing": 0.5,
    "loyalty": 0.3,
    "desperation_threshold": 0.6,
    "patience_years": 3,
    "deadline_activity": 0.9,
    "premium_position_focus": 0.55
  },

  "conservative": {
    "name": "Conservative",
    "description": "Cautious GM who rarely makes big moves, prefers stability and cap health",
    "risk_tolerance": 0.25,
    "win_now_mentality": 0.45,
    "draft_pick_value": 0.6,
    "cap_management": 0.85,
    "trade_frequency": 0.25,
    "veteran_preference": 0.5,
    "star_chasing": 0.2,
    "loyalty": 0.75,
    "desperation_threshold": 0.75,
    "patience_years": 4,
    "deadline_activity": 0.3,
    "premium_position_focus": 0.5
  },

  "draft_hoarder": {
    "name": "Draft Hoarder",
    "description": "GM obsessed with accumulating draft capital, trades down frequently",
    "risk_tolerance": 0.4,
    "win_now_mentality": 0.3,
    "draft_pick_value": 0.95,
    "cap_management": 0.65,
    "trade_frequency": 0.7,
    "veteran_preference": 0.25,
    "star_chasing": 0.15,
    "loyalty": 0.5,
    "desperation_threshold": 0.85,
    "patience_years": 6,
    "deadline_activity": 0.4,
    "premium_position_focus": 0.7
  },

  "star_chaser": {
    "name": "Star Chaser",
    "description": "GM who pursues elite talent aggressively, building around superstars",
    "risk_tolerance": 0.8,
    "win_now_mentality": 0.75,
    "draft_pick_value": 0.35,
    "cap_management": 0.3,
    "trade_frequency": 0.6,
    "veteran_preference": 0.65,
    "star_chasing": 0.9,
    "loyalty": 0.35,
    "desperation_threshold": 0.6,
    "patience_years": 2,
    "deadline_activity": 0.75,
    "premium_position_focus": 0.85
  }
}
```

---

## Step 3: Factory Pattern

**File**: `src/team_management/gm_archetype_factory.py`

```python
import json
from pathlib import Path
from typing import Dict, Optional
from .gm_archetype import GMArchetype

class GMArchetypeFactory:
    """
    Factory for loading and creating GM archetypes.

    Loads base templates from JSON and applies team-specific customizations.
    Caches loaded archetypes for performance.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize factory with config directory path.

        Args:
            config_path: Path to config directory (defaults to src/config)
        """
        if config_path is None:
            # Default to src/config relative to this file
            current_file = Path(__file__)
            src_dir = current_file.parent.parent
            config_path = src_dir / "config"

        self.config_path = config_path
        self.base_archetypes_path = config_path / "gm_archetypes" / "base_archetypes.json"
        self.gm_profiles_path = config_path / "gm_profiles"

        # Cache for loaded archetypes
        self._base_archetypes: Dict[str, GMArchetype] = {}
        self._team_archetypes: Dict[int, GMArchetype] = {}

        # Load base archetypes on initialization
        self._load_base_archetypes()

    def _load_base_archetypes(self):
        """Load all base archetype templates from JSON"""
        if not self.base_archetypes_path.exists():
            raise FileNotFoundError(
                f"Base archetypes file not found: {self.base_archetypes_path}"
            )

        with open(self.base_archetypes_path, 'r') as f:
            data = json.load(f)

        for key, archetype_data in data.items():
            self._base_archetypes[key] = GMArchetype.from_dict(archetype_data)

    def get_base_archetype(self, archetype_name: str) -> GMArchetype:
        """
        Get a base archetype template by name.

        Args:
            archetype_name: Name of archetype (win_now, rebuilder, etc.)

        Returns:
            GMArchetype instance

        Raises:
            ValueError: If archetype name not found
        """
        if archetype_name not in self._base_archetypes:
            available = ', '.join(self._base_archetypes.keys())
            raise ValueError(
                f"Unknown archetype '{archetype_name}'. Available: {available}"
            )

        return self._base_archetypes[archetype_name]

    def get_team_archetype(self, team_id: int) -> GMArchetype:
        """
        Get the GM archetype for a specific team.

        Loads from cache if available, otherwise loads from JSON config.

        Args:
            team_id: Team ID (1-32)

        Returns:
            GMArchetype instance for the team

        Raises:
            ValueError: If team_id is invalid
            FileNotFoundError: If team config file not found
        """
        if not 1 <= team_id <= 32:
            raise ValueError(f"team_id must be between 1 and 32, got {team_id}")

        # Check cache first
        if team_id in self._team_archetypes:
            return self._team_archetypes[team_id]

        # Load from file
        team_archetype = self._load_team_archetype(team_id)

        # Cache and return
        self._team_archetypes[team_id] = team_archetype
        return team_archetype

    def _load_team_archetype(self, team_id: int) -> GMArchetype:
        """
        Load team archetype from JSON config file.

        Args:
            team_id: Team ID (1-32)

        Returns:
            GMArchetype instance
        """
        # Find team config file
        team_files = list(self.gm_profiles_path.glob(f"team_{team_id:02d}_*.json"))

        if not team_files:
            raise FileNotFoundError(
                f"No GM profile found for team_id {team_id} in {self.gm_profiles_path}"
            )

        if len(team_files) > 1:
            raise ValueError(
                f"Multiple GM profiles found for team_id {team_id}: {team_files}"
            )

        # Load team config
        with open(team_files[0], 'r') as f:
            team_config = json.load(f)

        # Get base archetype
        base_archetype_name = team_config.get('base_archetype')
        if not base_archetype_name:
            raise ValueError(
                f"Team config {team_files[0]} missing 'base_archetype' field"
            )

        base_archetype = self.get_base_archetype(base_archetype_name.lower().replace('-', '_'))

        # Apply customizations if present
        customizations = team_config.get('customizations', {})
        if customizations:
            return base_archetype.apply_customizations(customizations)

        return base_archetype

    def get_all_team_archetypes(self) -> Dict[int, GMArchetype]:
        """
        Get archetypes for all 32 teams.

        Returns:
            Dict mapping team_id to GMArchetype
        """
        return {
            team_id: self.get_team_archetype(team_id)
            for team_id in range(1, 33)
        }

    def clear_cache(self):
        """Clear the team archetype cache"""
        self._team_archetypes.clear()

    def reload_team_archetype(self, team_id: int) -> GMArchetype:
        """
        Reload a team archetype from disk, bypassing cache.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Freshly loaded GMArchetype instance
        """
        if team_id in self._team_archetypes:
            del self._team_archetypes[team_id]

        return self.get_team_archetype(team_id)
```

---

## Step 4: Team GM Profile Configurations

**Directory**: `src/config/gm_profiles/`

### Template for Team Config Files

Each team gets a JSON file: `team_XX_team_name.json`

```json
{
  "team_id": 1,
  "team_name": "Arizona Cardinals",
  "base_archetype": "Balanced",
  "customizations": {
    "risk_tolerance": 0.6,
    "trade_frequency": 0.55
  },
  "notes": "Moderately active front office, willing to take calculated risks"
}
```

### All 32 Team Assignments

**Win-Now Teams** (base_archetype: "Win-Now"):
- Kansas City Chiefs (team_id: 15)
- Philadelphia Eagles (team_id: 23)
- San Francisco 49ers (team_id: 26)
- Buffalo Bills (team_id: 4)
- Cincinnati Bengals (team_id: 6)

**Rebuilder Teams** (base_archetype: "Rebuilder"):
- Chicago Bears (team_id: 5)
- New England Patriots (team_id: 21)
- Carolina Panthers (team_id: 3)
- New York Giants (team_id: 22)

**Balanced Teams** (base_archetype: "Balanced"):
- Arizona Cardinals (team_id: 1)
- Tampa Bay Buccaneers (team_id: 30)
- Pittsburgh Steelers (team_id: 24)
- Green Bay Packers (team_id: 12)
- Minnesota Vikings (team_id: 19)
- Seattle Seahawks (team_id: 27)
- Denver Broncos (team_id: 8)
- Atlanta Falcons (team_id: 2)
- Indianapolis Colts (team_id: 14)
- Tennessee Titans (team_id: 31)

**Aggressive Trader Teams** (base_archetype: "Aggressive Trader"):
- Los Angeles Rams (team_id: 17)
- Las Vegas Raiders (team_id: 16)
- Miami Dolphins (team_id: 18)
- Cleveland Browns (team_id: 7)

**Conservative Teams** (base_archetype: "Conservative"):
- New Orleans Saints (team_id: 20)
- New York Jets (team_id: 32)
- Jacksonville Jaguars (team_id: 13)

**Draft Hoarder Teams** (base_archetype: "Draft Hoarder"):
- Houston Texans (team_id: 11)
- Detroit Lions (team_id: 9) - *Note: Currently rebuilding but hoarding picks*

**Star Chaser Teams** (base_archetype: "Star Chaser"):
- Dallas Cowboys (team_id: 10)
- Los Angeles Chargers (team_id: 29)
- Baltimore Ravens (team_id: 28)
- Washington Commanders (team_id: 25)

---

## Step 5: Testing Strategy

### Unit Tests

**File**: `tests/team_management/test_gm_archetype.py`

```python
import pytest
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

    def test_patience_years_validation(self):
        """Test that patience_years must be 1-10"""
        with pytest.raises(ValueError, match="patience_years must be between"):
            GMArchetype(
                name="Invalid",
                description="Test",
                patience_years=15
            )

    def test_to_dict(self):
        """Test converting archetype to dictionary"""
        archetype = GMArchetype(
            name="Test",
            description="Test desc",
            risk_tolerance=0.6
        )
        data = archetype.to_dict()

        assert data['name'] == "Test"
        assert data['risk_tolerance'] == 0.6
        assert 'description' in data

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

    def test_json_serialization(self):
        """Test JSON serialization round-trip"""
        original = GMArchetype(
            name="Test",
            description="Test desc",
            risk_tolerance=0.8
        )

        json_str = original.to_json()
        restored = GMArchetype.from_json(json_str)

        assert restored.name == original.name
        assert restored.risk_tolerance == original.risk_tolerance

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
```

**File**: `tests/team_management/test_gm_archetype_factory.py`

```python
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

    def test_get_base_archetype_success(self, factory):
        """Test retrieving valid base archetype"""
        archetype = factory.get_base_archetype('win_now')

        assert archetype.name == "Win-Now"
        assert archetype.win_now_mentality > 0.7
        assert archetype.draft_pick_value < 0.4

    def test_get_base_archetype_invalid(self, factory):
        """Test retrieving invalid archetype raises ValueError"""
        with pytest.raises(ValueError, match="Unknown archetype"):
            factory.get_base_archetype('nonexistent')

    def test_get_team_archetype_valid(self, factory):
        """Test retrieving team archetype by ID"""
        archetype = factory.get_team_archetype(15)  # Chiefs

        assert isinstance(archetype, GMArchetype)
        assert archetype.name is not None

    def test_get_team_archetype_invalid_id(self, factory):
        """Test invalid team ID raises ValueError"""
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
        assert len(set(risk_values)) > 5
        assert min(risk_values) < 0.4
        assert max(risk_values) > 0.6
```

---

## Step 6: Integration Preparation

### Add to DatabaseAPI (if needed)

If GM archetypes need to be stored in database for historical tracking:

```python
# In src/database/api.py

def get_team_gm_archetype(self, team_id: int, season_year: int) -> Dict:
    """Get GM archetype for team in specific season"""
    # Implementation if needed for historical tracking

def update_team_gm_archetype(self, team_id: int, season_year: int, archetype_data: Dict):
    """Update GM archetype (e.g., coaching staff changes)"""
    # Implementation if needed
```

### Usage Example for Phase 1.2

```python
from src.team_management.gm_archetype_factory import GMArchetypeFactory

# Initialize factory
factory = GMArchetypeFactory()

# Get archetype for specific team
chiefs_gm = factory.get_team_archetype(15)

# Use in transaction decision
if chiefs_gm.trade_frequency > 0.6:
    print("Chiefs GM is an active trader")

# Check win-now mentality
if chiefs_gm.win_now_mentality > 0.7:
    print("Chiefs are in win-now mode")
```

---

## Success Criteria

### Functional Requirements
- ✅ GMArchetype dataclass with 12 traits (all 0.0-1.0 except patience_years)
- ✅ Validation ensures all traits within acceptable ranges
- ✅ 7 base archetype templates with distinct personalities
- ✅ 32 team configurations (one per NFL team)
- ✅ Factory pattern with caching for performance
- ✅ JSON serialization support for persistence

### Testing Requirements
- ✅ 100% test coverage on GMArchetype validation
- ✅ All 7 base archetypes load successfully
- ✅ All 32 team configs load without errors
- ✅ Factory caching works correctly
- ✅ Customizations properly override base values

### Quality Requirements
- ✅ Archetype diversity: Teams should span full 0.0-1.0 range on most traits
- ✅ Realistic assignments: Win-now teams have high win_now_mentality, rebuilders have high draft_pick_value
- ✅ Documentation: All traits have clear docstrings explaining meaning
- ✅ Type hints: All methods properly typed

---

## Implementation Checklist

- [ ] Create `src/team_management/gm_archetype.py`
- [ ] Create `src/team_management/gm_archetype_factory.py`
- [ ] Create `src/config/gm_archetypes/` directory
- [ ] Create `base_archetypes.json` with 7 templates
- [ ] Create `src/config/gm_profiles/` directory
- [ ] Create all 32 team JSON config files
- [ ] Create `tests/team_management/test_gm_archetype.py`
- [ ] Create `tests/team_management/test_gm_archetype_factory.py`
- [ ] Run all tests and ensure 100% pass rate
- [ ] Verify all 32 teams load correctly
- [ ] Document usage patterns for Phase 1.2

---

## Next Phase Preview

Once Phase 1.1 is complete, Phase 1.2 (Trade Value Calculator) will use GM archetypes to:
- Adjust trade valuations based on team needs
- Determine acceptable trade fairness thresholds
- Calculate transaction probability
- Drive AI decision-making logic

The archetype system is the foundation for all AI transaction behavior.
