# Player Generator System - Step-by-Step Development Plan

**Version**: 1.1
**Date**: October 5, 2025
**Status**: Sprint 1 Complete (Core Infrastructure)
**Target**: Flexible NFL player generation system supporting Draft, UDFA, International, and Custom contexts
**Reference Specification**: `docs/specifications/player_generator_system.md`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Success Criteria](#success-criteria)
3. [Development Philosophy](#development-philosophy)
4. [Implementation Sprints](#implementation-sprints)
   - [Sprint 1: Core Infrastructure](#sprint-1-core-infrastructure)
   - [Sprint 2: Basic Player Generation](#sprint-2-basic-player-generation)
   - [Sprint 3: Archetype System Foundation](#sprint-3-archetype-system-foundation)
   - [Sprint 4: Complete Archetype Library](#sprint-4-complete-archetype-library)
   - [Sprint 5: Draft Class Generation](#sprint-5-draft-class-generation)
   - [Sprint 6: Scouting System](#sprint-6-scouting-system)
   - [Sprint 7: Development Curves](#sprint-7-development-curves)
   - [Sprint 8: Traits & Names](#sprint-8-traits--names)
   - [Sprint 9: College & Background](#sprint-9-college--background)
   - [Sprint 10: Advanced Features](#sprint-10-advanced-features)
5. [Testing Strategy](#testing-strategy)
6. [Integration Points](#integration-points)
7. [Risk Assessment](#risk-assessment)
8. [Timeline & Milestones](#timeline--milestones)

---

## Executive Summary

### Goal

Create a comprehensive, flexible player generation system that can produce realistic NFL players for multiple contexts:
- **NFL Draft**: Incoming rookies with varying talent levels and development potential
- **UDFA (Undrafted Free Agents)**: Lower-rated players with specific strengths
- **International Players**: Players from CFL, XFL, European leagues with unique characteristics
- **Custom Generation**: Designer-controlled player creation for specific scenarios

### Current State

- **Existing Player Structure**: Well-defined `Player` class with position-specific attributes
- **Contract System**: Established contract structure with salary cap integration
- **Draft Events**: Basic `DraftPickEvent` framework exists
- **Database**: Team-based player storage with JSON format
- **Gap**: No procedural generation system for creating new players

### Target State

- **Archetype-Based Generation**: 30+ position-specific templates with realistic attribute distributions
- **Statistical Realism**: Normal and beta distributions matching real NFL talent spreads
- **Scouting Uncertainty**: Separation of true vs scouted ratings for draft risk
- **Development System**: Age-based growth curves with peak performance periods
- **Player Conversion**: Clean conversion to existing Player class format

### Key Benefits

- **Realistic Draft Classes**: Varied talent with busts, reaches, and hidden gems
- **Repeatable Process**: Consistent player quality across multiple generations
- **Designer Flexibility**: Full control over generation parameters when needed
- **Statistical Authenticity**: Attributes that mirror real NFL distributions
- **Long-term Value**: Development curves and scouting create interesting player profiles

---

## Success Criteria

### Functional Requirements

✅ **FR-1**: Generate complete draft classes (262 players, rounds 1-7) with realistic talent distribution
✅ **FR-2**: Support UDFA generation with appropriate skill caps (50-65 overall ceiling)
✅ **FR-3**: Handle international player generation from multiple leagues (CFL, XFL, European)
✅ **FR-4**: Provide archetype-based generation for all 24 positions
✅ **FR-5**: Implement scouting system with confidence levels and error margins
✅ **FR-6**: Create development curves with position-specific peak ages
✅ **FR-7**: Support trait assignment (special abilities and weaknesses)
✅ **FR-8**: Generate realistic player backgrounds (college, hometown, combine stats)

### Technical Requirements

✅ **TR-1**: Statistical distribution system (normal, beta, bounded) for attributes
✅ **TR-2**: Attribute correlation engine (size/speed, experience/awareness)
✅ **TR-3**: Position-specific validation and constraints
✅ **TR-4**: JSON-based archetype definitions for designer modification
✅ **TR-5**: Comprehensive test coverage (>80% for core generation logic)
✅ **TR-6**: Performance optimization (generate 262-player class in <5 seconds)
✅ **TR-7**: Conversion to existing Player class format

### Quality Requirements

✅ **QR-1**: Realistic attribute distributions matching NFL statistical profiles
✅ **QR-2**: Balanced draft classes (no all-superstar or all-bust classes)
✅ **QR-3**: Position scarcity modeling (premium positions harder to fill)
✅ **QR-4**: Injury risk correlation with physical attributes
✅ **QR-5**: Consistent scouting accuracy (grades match true talent ±10 points on average)

---

## Development Philosophy

### Testability First

Each step in this plan is designed to be **independently testable** with clear success criteria. Every sprint delivers functional, validated components that can be verified in isolation before moving to the next phase.

### Bottom-Up Construction

We build foundational infrastructure first, then layer complexity:
1. Core statistics and distributions
2. Basic player generation
3. Archetype system
4. Advanced features (scouting, development, traits)
5. Integration with existing systems

### Incremental Validation

After each step, we validate:
- **Unit Tests**: Component-level functionality
- **Integration Tests**: Interaction with existing systems
- **Statistical Tests**: Distributions match expected profiles
- **Manual Verification**: Generated players "look right" to NFL observers

---

## Implementation Sprints

### Sprint 1: Core Infrastructure
**Duration**: 3-4 days
**Goal**: Establish statistical foundation and basic data structures

#### Step 1: Create Statistical Distribution Module
**File**: `src/player_generation/core/distributions.py`

**Implementation**:
```python
import random
import numpy as np
from typing import Tuple

class AttributeDistribution:
    """Statistical distributions for player attribute generation."""

    @staticmethod
    def normal(mean: float, std_dev: float, min_val: float, max_val: float) -> int:
        """Generate value from bounded normal distribution."""
        value = random.gauss(mean, std_dev)
        return int(max(min_val, min(max_val, value)))

    @staticmethod
    def beta(alpha: float, beta: float, min_val: float, max_val: float) -> int:
        """Generate value from beta distribution."""
        value = np.random.beta(alpha, beta)
        scaled = min_val + (max_val - min_val) * value
        return int(scaled)

    @staticmethod
    def weighted_choice(choices: list[Tuple[str, float]]) -> str:
        """Select from weighted choices."""
        weights = [w for _, w in choices]
        return random.choices([c for c, _ in choices], weights=weights)[0]
```

**Test Cases**:
```python
def test_normal_distribution_respects_bounds():
    """Verify normal distribution stays within min/max."""
    for _ in range(1000):
        val = AttributeDistribution.normal(mean=70, std_dev=10, min_val=40, max_val=99)
        assert 40 <= val <= 99

def test_beta_distribution_shape():
    """Verify beta distribution creates expected shape."""
    values = [AttributeDistribution.beta(2, 5, 40, 99) for _ in range(1000)]
    mean_val = sum(values) / len(values)
    assert 50 <= mean_val <= 65  # Alpha=2, Beta=5 skews low

def test_weighted_choice_distribution():
    """Verify weighted choices follow probability distribution."""
    choices = [("A", 0.7), ("B", 0.2), ("C", 0.1)]
    results = [AttributeDistribution.weighted_choice(choices) for _ in range(1000)]
    assert results.count("A") > results.count("B") > results.count("C")
```

**Acceptance Criteria**:
- ✅ Normal distribution generates values within specified bounds
- ✅ Beta distribution produces expected statistical shape
- ✅ Weighted choice respects probability weights
- ✅ All statistical tests pass with p-value > 0.05

---

#### Step 2: Create Attribute Correlation System
**File**: `src/player_generation/core/correlations.py`

**Implementation**:
```python
from typing import Dict, Optional
import random

class AttributeCorrelation:
    """Manages correlated attribute generation."""

    # Correlation coefficients (-1.0 to 1.0)
    CORRELATIONS = {
        ("size", "speed"): -0.6,  # Bigger players are slower
        ("strength", "size"): 0.7,  # Bigger players are stronger
        ("awareness", "experience"): 0.8,  # Experience improves awareness
        ("acceleration", "speed"): 0.9,  # Speed and acceleration highly correlated
        ("agility", "size"): -0.5,  # Bigger players less agile
    }

    @staticmethod
    def apply_correlation(
        base_value: int,
        correlated_attr: str,
        base_attr: str,
        target_mean: int,
        target_std: int
    ) -> int:
        """Apply correlation between two attributes."""
        correlation = AttributeCorrelation.CORRELATIONS.get((base_attr, correlated_attr), 0)

        if correlation == 0:
            # No correlation - use pure random
            return random.gauss(target_mean, target_std)

        # Calculate correlated value
        base_deviation = (base_value - target_mean) / target_std
        correlated_deviation = correlation * base_deviation
        correlated_value = target_mean + (correlated_deviation * target_std)

        # Add some random noise
        noise = random.gauss(0, target_std * 0.3)
        final_value = correlated_value + noise

        return int(max(40, min(99, final_value)))

    @staticmethod
    def get_correlation(attr1: str, attr2: str) -> float:
        """Get correlation coefficient between two attributes."""
        return AttributeCorrelation.CORRELATIONS.get((attr1, attr2),
               AttributeCorrelation.CORRELATIONS.get((attr2, attr1), 0))
```

**Test Cases**:
```python
def test_negative_correlation_size_speed():
    """High size should correlate with lower speed."""
    high_size_speeds = []
    low_size_speeds = []

    for _ in range(100):
        high_speed = AttributeCorrelation.apply_correlation(
            base_value=95, correlated_attr="speed", base_attr="size",
            target_mean=70, target_std=10
        )
        low_speed = AttributeCorrelation.apply_correlation(
            base_value=60, correlated_attr="speed", base_attr="size",
            target_mean=70, target_std=10
        )
        high_size_speeds.append(high_speed)
        low_size_speeds.append(low_speed)

    # High size should produce lower speeds on average
    assert sum(high_size_speeds) / 100 < sum(low_size_speeds) / 100

def test_positive_correlation_strength_size():
    """High size should correlate with higher strength."""
    high_size_str = []
    low_size_str = []

    for _ in range(100):
        high_str = AttributeCorrelation.apply_correlation(
            base_value=95, correlated_attr="strength", base_attr="size",
            target_mean=70, target_std=10
        )
        low_str = AttributeCorrelation.apply_correlation(
            base_value=60, correlated_attr="strength", base_attr="size",
            target_mean=70, target_std=10
        )
        high_size_str.append(high_str)
        low_size_str.append(low_str)

    # High size should produce higher strength on average
    assert sum(high_size_str) / 100 > sum(low_size_str) / 100
```

**Acceptance Criteria**:
- ✅ Negative correlations produce inverse relationships
- ✅ Positive correlations produce direct relationships
- ✅ Correlation strength matches coefficient magnitude
- ✅ Output values remain within valid bounds (40-99)

---

#### Step 3: Create Player Archetype Base Class
**File**: `src/player_generation/archetypes/base_archetype.py`

**Implementation**:
```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class Position(Enum):
    """NFL positions."""
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    # ... all positions

@dataclass
class AttributeRange:
    """Range for attribute generation."""
    min: int
    max: int
    mean: int
    std_dev: int

    def validate(self) -> bool:
        """Ensure range is valid."""
        return (40 <= self.min <= self.max <= 99 and
                self.min <= self.mean <= self.max)

@dataclass
class PlayerArchetype:
    """Base archetype definition for player generation."""

    # Identity
    archetype_id: str
    position: Position
    name: str
    description: str

    # Attribute ranges
    physical_attributes: Dict[str, AttributeRange]
    mental_attributes: Dict[str, AttributeRange]
    position_attributes: Dict[str, AttributeRange]

    # Constraints
    overall_range: AttributeRange
    frequency: float  # 0.0-1.0 (how common this archetype is)

    # Development
    peak_age_range: tuple[int, int]  # (min, max) peak age
    development_curve: str  # "early", "normal", "late"

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate archetype configuration."""
        # Check all ranges
        for attr_dict in [self.physical_attributes, self.mental_attributes,
                          self.position_attributes]:
            for name, range_obj in attr_dict.items():
                if not range_obj.validate():
                    return False, f"Invalid range for {name}"

        # Check frequency
        if not 0 <= self.frequency <= 1:
            return False, f"Invalid frequency: {self.frequency}"

        # Check peak age
        if not 20 <= self.peak_age_range[0] <= self.peak_age_range[1] <= 35:
            return False, f"Invalid peak age range: {self.peak_age_range}"

        return True, None

    def get_attribute_names(self) -> List[str]:
        """Get all attribute names for this archetype."""
        all_attrs = []
        all_attrs.extend(self.physical_attributes.keys())
        all_attrs.extend(self.mental_attributes.keys())
        all_attrs.extend(self.position_attributes.keys())
        return all_attrs
```

**Test Cases**:
```python
def test_archetype_creation():
    """Verify archetype can be created with valid data."""
    archetype = PlayerArchetype(
        archetype_id="pocket_passer_qb",
        position=Position.QB,
        name="Pocket Passer",
        description="Traditional pocket quarterback",
        physical_attributes={
            "speed": AttributeRange(min=65, max=80, mean=72, std_dev=5),
            "strength": AttributeRange(min=70, max=85, mean=77, std_dev=5)
        },
        mental_attributes={
            "awareness": AttributeRange(min=75, max=95, mean=85, std_dev=5)
        },
        position_attributes={
            "accuracy": AttributeRange(min=80, max=99, mean=90, std_dev=5)
        },
        overall_range=AttributeRange(min=70, max=95, mean=82, std_dev=8),
        frequency=0.3,
        peak_age_range=(28, 32),
        development_curve="normal"
    )

    is_valid, error = archetype.validate()
    assert is_valid
    assert error is None

def test_archetype_validation_catches_invalid_ranges():
    """Verify validation catches invalid attribute ranges."""
    archetype = PlayerArchetype(
        archetype_id="test",
        position=Position.QB,
        name="Test",
        description="Test archetype",
        physical_attributes={
            "speed": AttributeRange(min=100, max=110, mean=105, std_dev=5)  # Invalid!
        },
        mental_attributes={},
        position_attributes={},
        overall_range=AttributeRange(min=70, max=90, mean=80, std_dev=5),
        frequency=0.5,
        peak_age_range=(25, 30),
        development_curve="normal"
    )

    is_valid, error = archetype.validate()
    assert not is_valid
    assert "Invalid range" in error
```

**Acceptance Criteria**:
- ✅ Archetype class can store all necessary configuration
- ✅ Validation catches invalid ranges and frequencies
- ✅ Can retrieve all attribute names for generation
- ✅ Dataclass provides clean serialization for JSON

---

#### Step 4: Create Player Generation Context
**File**: `src/player_generation/core/generation_context.py`

**Implementation**:
```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class GenerationContext(Enum):
    """Context for player generation."""
    NFL_DRAFT = "nfl_draft"
    UDFA = "udfa"
    INTERNATIONAL_CFL = "international_cfl"
    INTERNATIONAL_XFL = "international_xfl"
    INTERNATIONAL_EUROPE = "international_europe"
    CUSTOM = "custom"

@dataclass
class GenerationConfig:
    """Configuration for player generation."""

    # Core settings
    context: GenerationContext
    position: Optional[str] = None
    archetype_id: Optional[str] = None

    # Draft-specific
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None
    draft_year: Optional[int] = None

    # Talent modifiers
    overall_min: int = 40
    overall_max: int = 99
    talent_modifier: float = 1.0  # Multiplier for attribute ranges

    # Scouting
    enable_scouting_error: bool = True
    scouting_confidence: Optional[str] = None  # "high", "medium", "low"

    # Development
    age: Optional[int] = None
    development_override: Optional[str] = None  # Override development curve

    def get_overall_range(self) -> tuple[int, int]:
        """Calculate overall range based on context and round."""
        if self.context == GenerationContext.NFL_DRAFT and self.draft_round:
            # Draft round affects overall range
            ranges = {
                1: (75, 95),  # First round: elite talent
                2: (70, 88),  # Second round: quality starters
                3: (68, 85),  # Third round: good players
                4: (65, 82),  # Fourth round: rotational players
                5: (62, 78),  # Fifth round: backups
                6: (60, 75),  # Sixth round: depth
                7: (55, 72),  # Seventh round: projects
            }
            min_val, max_val = ranges.get(self.draft_round, (55, 72))

        elif self.context == GenerationContext.UDFA:
            min_val, max_val = 50, 68  # UDFA ceiling

        elif self.context in [GenerationContext.INTERNATIONAL_CFL,
                               GenerationContext.INTERNATIONAL_XFL]:
            min_val, max_val = 55, 75  # International range

        else:
            min_val, max_val = self.overall_min, self.overall_max

        return min_val, max_val

    def get_scouting_error_margin(self) -> int:
        """Get scouting error margin based on confidence."""
        if not self.enable_scouting_error:
            return 0

        margins = {
            "high": 3,
            "medium": 7,
            "low": 12,
            None: 7  # default
        }
        return margins.get(self.scouting_confidence, 7)
```

**Test Cases**:
```python
def test_draft_context_overall_ranges():
    """Verify draft rounds produce appropriate overall ranges."""
    configs = [
        (1, 75, 95),
        (3, 68, 85),
        (7, 55, 72)
    ]

    for round_num, expected_min, expected_max in configs:
        config = GenerationConfig(
            context=GenerationContext.NFL_DRAFT,
            draft_round=round_num
        )
        min_val, max_val = config.get_overall_range()
        assert min_val == expected_min
        assert max_val == expected_max

def test_udfa_context_caps_overall():
    """Verify UDFA context limits overall ceiling."""
    config = GenerationConfig(context=GenerationContext.UDFA)
    min_val, max_val = config.get_overall_range()
    assert max_val <= 68  # UDFA ceiling

def test_scouting_error_margins():
    """Verify scouting confidence affects error margin."""
    high_conf = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        scouting_confidence="high"
    )
    low_conf = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        scouting_confidence="low"
    )

    assert high_conf.get_scouting_error_margin() < low_conf.get_scouting_error_margin()
```

**Acceptance Criteria**:
- ✅ Context enum covers all generation scenarios
- ✅ Draft round correctly influences overall ranges
- ✅ UDFA context caps overall ceiling appropriately
- ✅ Scouting error scales with confidence level
- ✅ Config class provides all necessary generation parameters

---

#### Step 5: Create Generated Player Data Model
**File**: `src/player_generation/models/generated_player.py`

**Implementation**:
```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import date

@dataclass
class ScoutingReport:
    """Scouting evaluation of a player."""
    scouted_overall: int
    true_overall: int
    error_margin: int
    confidence: str  # "high", "medium", "low"
    strengths: List[str]
    weaknesses: List[str]
    comparison: str  # "Plays like [NFL Player]"
    scouting_grade: str  # "A+", "A", "B+", etc.

    def get_grade_from_overall(overall: int) -> str:
        """Convert overall to scouting grade."""
        if overall >= 90: return "A+"
        if overall >= 85: return "A"
        if overall >= 80: return "A-"
        if overall >= 75: return "B+"
        if overall >= 70: return "B"
        if overall >= 65: return "B-"
        if overall >= 60: return "C+"
        return "C"

@dataclass
class PlayerBackground:
    """Player background information."""
    college: str
    hometown: str
    home_state: str

    # Combine stats (if applicable)
    forty_yard_dash: Optional[float] = None
    bench_press: Optional[int] = None
    vertical_jump: Optional[float] = None
    broad_jump: Optional[int] = None
    three_cone: Optional[float] = None
    shuttle: Optional[float] = None

    # College production
    college_games_played: Optional[int] = None
    college_stats: Dict[str, float] = field(default_factory=dict)

@dataclass
class DevelopmentProfile:
    """Player development trajectory."""
    current_age: int
    peak_age_min: int
    peak_age_max: int
    development_curve: str  # "early", "normal", "late"
    growth_rate: float  # Points per year during growth phase
    decline_rate: float  # Points per year during decline phase

    def is_in_growth_phase(self) -> bool:
        """Check if player is still developing."""
        return self.current_age < self.peak_age_min

    def is_in_peak_phase(self) -> bool:
        """Check if player is in peak years."""
        return self.peak_age_min <= self.current_age <= self.peak_age_max

    def is_in_decline_phase(self) -> bool:
        """Check if player is declining."""
        return self.current_age > self.peak_age_max

@dataclass
class GeneratedPlayer:
    """Complete generated player with all metadata."""

    # Core identity
    player_id: str
    name: str
    position: str
    age: int
    jersey_number: Optional[int] = None

    # Attributes
    true_ratings: Dict[str, int] = field(default_factory=dict)
    scouted_ratings: Dict[str, int] = field(default_factory=dict)

    # Overall ratings
    true_overall: int = 0
    scouted_overall: int = 0

    # Metadata
    archetype_id: str = ""
    generation_context: str = ""

    # Optional components
    scouting_report: Optional[ScoutingReport] = None
    background: Optional[PlayerBackground] = None
    development: Optional[DevelopmentProfile] = None
    traits: List[str] = field(default_factory=list)

    # Draft metadata
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None

    def to_player_dict(self) -> Dict:
        """Convert to Player class compatible dictionary."""
        return {
            "name": self.name,
            "number": self.jersey_number or 0,
            "primary_position": self.position,
            "ratings": self.true_ratings,
            "age": self.age,
            "traits": self.traits
        }

    def get_display_overall(self) -> int:
        """Get overall rating for display (scouted if available)."""
        return self.scouted_overall if self.scouted_overall > 0 else self.true_overall
```

**Test Cases**:
```python
def test_generated_player_creation():
    """Verify GeneratedPlayer can be created with complete data."""
    player = GeneratedPlayer(
        player_id="DRAFT_2025_001",
        name="John Smith",
        position="QB",
        age=22,
        jersey_number=12,
        true_ratings={"accuracy": 85, "arm_strength": 88},
        scouted_ratings={"accuracy": 82, "arm_strength": 90},
        true_overall=86,
        scouted_overall=85,
        archetype_id="pocket_passer_qb",
        generation_context="nfl_draft",
        draft_round=1,
        draft_pick=15
    )

    assert player.player_id == "DRAFT_2025_001"
    assert player.get_display_overall() == 85  # Shows scouted

def test_development_profile_phase_detection():
    """Verify development profile correctly identifies phases."""
    # Growth phase
    growth = DevelopmentProfile(
        current_age=23, peak_age_min=27, peak_age_max=31,
        development_curve="normal", growth_rate=2.0, decline_rate=1.5
    )
    assert growth.is_in_growth_phase()
    assert not growth.is_in_peak_phase()

    # Peak phase
    peak = DevelopmentProfile(
        current_age=29, peak_age_min=27, peak_age_max=31,
        development_curve="normal", growth_rate=2.0, decline_rate=1.5
    )
    assert peak.is_in_peak_phase()

    # Decline phase
    decline = DevelopmentProfile(
        current_age=33, peak_age_min=27, peak_age_max=31,
        development_curve="normal", growth_rate=2.0, decline_rate=1.5
    )
    assert decline.is_in_decline_phase()

def test_player_to_dict_conversion():
    """Verify conversion to Player class format."""
    player = GeneratedPlayer(
        player_id="TEST_001",
        name="Test Player",
        position="WR",
        age=24,
        jersey_number=80,
        true_ratings={"speed": 90, "catching": 85}
    )

    player_dict = player.to_player_dict()
    assert player_dict["name"] == "Test Player"
    assert player_dict["primary_position"] == "WR"
    assert player_dict["ratings"]["speed"] == 90
```

**Acceptance Criteria**:
- ✅ GeneratedPlayer model contains all necessary data
- ✅ ScoutingReport tracks evaluation and error
- ✅ DevelopmentProfile correctly identifies career phases
- ✅ PlayerBackground stores college and combine data
- ✅ Conversion to Player class format works correctly

---

#### Step 6: Create Archetype Registry and Loader
**File**: `src/player_generation/archetypes/archetype_registry.py`

**Implementation**:
```python
from typing import Dict, List, Optional
import json
from pathlib import Path
from .base_archetype import PlayerArchetype, Position
import random

class ArchetypeRegistry:
    """Central registry for player archetypes."""

    def __init__(self, config_dir: str = "src/config/archetypes/"):
        self.config_dir = Path(config_dir)
        self.archetypes: Dict[str, PlayerArchetype] = {}
        self._load_archetypes()

    def _load_archetypes(self):
        """Load all archetype definitions from JSON files."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return

        for json_file in self.config_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                archetype = self._dict_to_archetype(data)
                is_valid, error = archetype.validate()
                if is_valid:
                    self.archetypes[archetype.archetype_id] = archetype
                else:
                    print(f"Invalid archetype {archetype.archetype_id}: {error}")

    def _dict_to_archetype(self, data: Dict) -> PlayerArchetype:
        """Convert JSON dict to PlayerArchetype object."""
        # Convert attribute dicts to AttributeRange objects
        def parse_attrs(attrs_dict):
            from .base_archetype import AttributeRange
            return {
                name: AttributeRange(**range_data)
                for name, range_data in attrs_dict.items()
            }

        return PlayerArchetype(
            archetype_id=data["archetype_id"],
            position=Position[data["position"]],
            name=data["name"],
            description=data["description"],
            physical_attributes=parse_attrs(data["physical_attributes"]),
            mental_attributes=parse_attrs(data["mental_attributes"]),
            position_attributes=parse_attrs(data["position_attributes"]),
            overall_range=AttributeRange(**data["overall_range"]),
            frequency=data["frequency"],
            peak_age_range=tuple(data["peak_age_range"]),
            development_curve=data["development_curve"]
        )

    def get_archetype(self, archetype_id: str) -> Optional[PlayerArchetype]:
        """Get archetype by ID."""
        return self.archetypes.get(archetype_id)

    def get_archetypes_by_position(self, position: str) -> List[PlayerArchetype]:
        """Get all archetypes for a position."""
        pos_enum = Position[position]
        return [a for a in self.archetypes.values() if a.position == pos_enum]

    def select_random_archetype(self, position: str) -> Optional[PlayerArchetype]:
        """Select random archetype for position weighted by frequency."""
        archetypes = self.get_archetypes_by_position(position)
        if not archetypes:
            return None

        # Weight by frequency
        weights = [a.frequency for a in archetypes]
        return random.choices(archetypes, weights=weights)[0]

    def list_all_archetypes(self) -> List[str]:
        """Get list of all archetype IDs."""
        return list(self.archetypes.keys())

    def get_archetype_count(self) -> int:
        """Get total number of registered archetypes."""
        return len(self.archetypes)
```

**Test Cases**:
```python
def test_archetype_registry_initialization():
    """Verify registry initializes correctly."""
    registry = ArchetypeRegistry()
    assert registry is not None
    assert isinstance(registry.archetypes, dict)

def test_get_archetypes_by_position():
    """Verify position filtering works."""
    registry = ArchetypeRegistry()

    # Create test archetypes
    from .base_archetype import PlayerArchetype, Position, AttributeRange
    qb_archetype = PlayerArchetype(
        archetype_id="test_qb",
        position=Position.QB,
        name="Test QB",
        description="Test",
        physical_attributes={},
        mental_attributes={},
        position_attributes={},
        overall_range=AttributeRange(70, 90, 80, 5),
        frequency=1.0,
        peak_age_range=(27, 31),
        development_curve="normal"
    )
    registry.archetypes["test_qb"] = qb_archetype

    qb_archetypes = registry.get_archetypes_by_position("QB")
    assert len(qb_archetypes) >= 1
    assert all(a.position == Position.QB for a in qb_archetypes)

def test_weighted_archetype_selection():
    """Verify frequency-weighted selection."""
    registry = ArchetypeRegistry()

    # Mock archetypes with different frequencies
    from .base_archetype import PlayerArchetype, Position, AttributeRange

    common = PlayerArchetype(
        archetype_id="common", position=Position.WR, name="Common", description="",
        physical_attributes={}, mental_attributes={}, position_attributes={},
        overall_range=AttributeRange(70, 90, 80, 5),
        frequency=0.8, peak_age_range=(27, 31), development_curve="normal"
    )
    rare = PlayerArchetype(
        archetype_id="rare", position=Position.WR, name="Rare", description="",
        physical_attributes={}, mental_attributes={}, position_attributes={},
        overall_range=AttributeRange(70, 90, 80, 5),
        frequency=0.2, peak_age_range=(27, 31), development_curve="normal"
    )

    registry.archetypes["common"] = common
    registry.archetypes["rare"] = rare

    # Select 100 times, common should appear more
    selections = [registry.select_random_archetype("WR").archetype_id
                  for _ in range(100)]
    assert selections.count("common") > selections.count("rare")
```

**Acceptance Criteria**:
- ✅ Registry can load archetypes from JSON files
- ✅ Position filtering returns correct archetypes
- ✅ Weighted selection respects frequency values
- ✅ Registry provides query methods for archetype access
- ✅ Invalid archetypes are rejected with clear error messages

---

### Sprint 1 Completion Summary

**Status**: ✅ **COMPLETE** (October 5, 2025)

**Implemented Components**:
1. ✅ Statistical Distribution Module (`src/player_generation/core/distributions.py`)
2. ✅ Attribute Correlation System (`src/player_generation/core/correlations.py`)
3. ✅ Player Archetype Base Class (`src/player_generation/archetypes/base_archetype.py`)
4. ✅ Player Generation Context (`src/player_generation/core/generation_context.py`)
5. ✅ Generated Player Data Model (`src/player_generation/models/generated_player.py`)
6. ✅ Archetype Registry and Loader (`src/player_generation/archetypes/archetype_registry.py`)

**Test Results**:
- **Total Tests**: 21 tests
- **Test Status**: All passing (100%)
- **Test File**: `tests/player_generation/test_sprint1.py`
- **Coverage**: Core infrastructure components fully tested

**Key Achievements**:
- Complete directory structure created under `src/player_generation/`
- All 6 core infrastructure components implemented and tested
- Statistical distribution system operational with normal and beta distributions
- Attribute correlation engine working with negative/positive correlations
- Archetype system foundation complete with validation
- Generation context supports all target scenarios (Draft, UDFA, International, Custom)
- Player data model ready for integration with existing Player class

**Next Steps**:
- Proceed to Sprint 2 for basic player generation implementation
- Begin implementing attribute generator and name generator
- Create core player generator with archetype selection

---

### Sprint 2: Basic Player Generation
**Duration**: 3-4 days
**Goal**: Implement core player generation logic

#### Step 7: Create Attribute Generator
**File**: `src/player_generation/generators/attribute_generator.py`

**Implementation**:
```python
from typing import Dict
from ..core.distributions import AttributeDistribution
from ..core.correlations import AttributeCorrelation
from ..archetypes.base_archetype import PlayerArchetype, AttributeRange

class AttributeGenerator:
    """Generates player attributes based on archetype."""

    @staticmethod
    def generate_attributes(archetype: PlayerArchetype) -> Dict[str, int]:
        """Generate all attributes for a player based on archetype."""
        attributes = {}

        # Step 1: Generate physical attributes first (they affect others)
        physical_attrs = AttributeGenerator._generate_physical_attributes(
            archetype.physical_attributes
        )
        attributes.update(physical_attrs)

        # Step 2: Generate mental attributes
        mental_attrs = AttributeGenerator._generate_mental_attributes(
            archetype.mental_attributes
        )
        attributes.update(mental_attrs)

        # Step 3: Generate position-specific attributes with correlations
        position_attrs = AttributeGenerator._generate_position_attributes(
            archetype.position_attributes,
            physical_attrs
        )
        attributes.update(position_attrs)

        return attributes

    @staticmethod
    def _generate_physical_attributes(attr_ranges: Dict[str, AttributeRange]) -> Dict[str, int]:
        """Generate physical attributes with correlations."""
        attributes = {}

        # Generate size first if it exists (affects other physicals)
        if "size" in attr_ranges:
            size_range = attr_ranges["size"]
            attributes["size"] = AttributeDistribution.normal(
                size_range.mean, size_range.std_dev,
                size_range.min, size_range.max
            )

        # Generate other physical attributes with correlations
        for attr_name, attr_range in attr_ranges.items():
            if attr_name == "size":
                continue  # Already generated

            if "size" in attributes:
                # Apply size correlation
                attributes[attr_name] = AttributeCorrelation.apply_correlation(
                    base_value=attributes["size"],
                    correlated_attr=attr_name,
                    base_attr="size",
                    target_mean=attr_range.mean,
                    target_std=attr_range.std_dev
                )
            else:
                # No correlation
                attributes[attr_name] = AttributeDistribution.normal(
                    attr_range.mean, attr_range.std_dev,
                    attr_range.min, attr_range.max
                )

        return attributes

    @staticmethod
    def _generate_mental_attributes(attr_ranges: Dict[str, AttributeRange]) -> Dict[str, int]:
        """Generate mental attributes."""
        attributes = {}

        # Mental attributes are mostly independent
        for attr_name, attr_range in attr_ranges.items():
            attributes[attr_name] = AttributeDistribution.normal(
                attr_range.mean, attr_range.std_dev,
                attr_range.min, attr_range.max
            )

        return attributes

    @staticmethod
    def _generate_position_attributes(
        attr_ranges: Dict[str, AttributeRange],
        physical_attrs: Dict[str, int]
    ) -> Dict[str, int]:
        """Generate position attributes with physical correlations."""
        attributes = {}

        for attr_name, attr_range in attr_ranges.items():
            # Check for relevant correlations
            if attr_name == "speed" and "size" in physical_attrs:
                attributes[attr_name] = AttributeCorrelation.apply_correlation(
                    base_value=physical_attrs["size"],
                    correlated_attr="speed",
                    base_attr="size",
                    target_mean=attr_range.mean,
                    target_std=attr_range.std_dev
                )
            else:
                attributes[attr_name] = AttributeDistribution.normal(
                    attr_range.mean, attr_range.std_dev,
                    attr_range.min, attr_range.max
                )

        return attributes

    @staticmethod
    def calculate_overall(attributes: Dict[str, int], position: str) -> int:
        """Calculate overall rating based on position-weighted attributes."""
        # Position-specific weights
        weights = {
            "QB": {"accuracy": 0.25, "arm_strength": 0.20, "awareness": 0.20,
                   "speed": 0.10, "agility": 0.10, "strength": 0.15},
            "RB": {"speed": 0.25, "agility": 0.20, "strength": 0.15,
                   "carrying": 0.15, "vision": 0.15, "elusiveness": 0.10},
            "WR": {"speed": 0.25, "catching": 0.25, "route_running": 0.20,
                   "agility": 0.15, "awareness": 0.15},
            # ... more positions
        }

        position_weights = weights.get(position, {})
        if not position_weights:
            # Fallback: average all attributes
            return int(sum(attributes.values()) / len(attributes))

        weighted_sum = sum(
            attributes.get(attr, 70) * weight
            for attr, weight in position_weights.items()
        )

        return int(weighted_sum)
```

**Test Cases**:
```python
def test_attribute_generation_respects_ranges():
    """Verify generated attributes fall within archetype ranges."""
    from ..archetypes.base_archetype import PlayerArchetype, Position, AttributeRange

    archetype = PlayerArchetype(
        archetype_id="test",
        position=Position.QB,
        name="Test",
        description="Test archetype",
        physical_attributes={
            "speed": AttributeRange(min=65, max=80, mean=72, std_dev=5)
        },
        mental_attributes={
            "awareness": AttributeRange(min=75, max=95, mean=85, std_dev=5)
        },
        position_attributes={
            "accuracy": AttributeRange(min=80, max=99, mean=90, std_dev=5)
        },
        overall_range=AttributeRange(min=70, max=95, mean=82, std_dev=8),
        frequency=1.0,
        peak_age_range=(28, 32),
        development_curve="normal"
    )

    # Generate 100 players to test distribution
    for _ in range(100):
        attrs = AttributeGenerator.generate_attributes(archetype)
        assert 65 <= attrs["speed"] <= 80
        assert 75 <= attrs["awareness"] <= 95
        assert 80 <= attrs["accuracy"] <= 99

def test_size_speed_correlation():
    """Verify size negatively correlates with speed."""
    from ..archetypes.base_archetype import PlayerArchetype, Position, AttributeRange

    # Create archetype with size and speed
    archetype = PlayerArchetype(
        archetype_id="test",
        position=Position.RB,
        name="Test",
        description="Test",
        physical_attributes={
            "size": AttributeRange(min=60, max=95, mean=77, std_dev=10),
            "speed": AttributeRange(min=70, max=95, mean=82, std_dev=8)
        },
        mental_attributes={},
        position_attributes={},
        overall_range=AttributeRange(min=70, max=90, mean=80, std_dev=5),
        frequency=1.0,
        peak_age_range=(25, 29),
        development_curve="normal"
    )

    # Generate many players and track correlation
    high_size_speeds = []
    low_size_speeds = []

    for _ in range(100):
        attrs = AttributeGenerator.generate_attributes(archetype)
        if attrs["size"] > 85:
            high_size_speeds.append(attrs["speed"])
        elif attrs["size"] < 70:
            low_size_speeds.append(attrs["speed"])

    # Low size players should be faster on average
    if high_size_speeds and low_size_speeds:
        avg_high_size_speed = sum(high_size_speeds) / len(high_size_speeds)
        avg_low_size_speed = sum(low_size_speeds) / len(low_size_speeds)
        assert avg_low_size_speed > avg_high_size_speed

def test_overall_calculation():
    """Verify overall rating calculation."""
    attributes = {
        "accuracy": 90,
        "arm_strength": 85,
        "awareness": 88,
        "speed": 75,
        "agility": 78,
        "strength": 80
    }

    overall = AttributeGenerator.calculate_overall(attributes, "QB")
    assert 75 <= overall <= 95  # Should be in reasonable range
```

**Acceptance Criteria**:
- ✅ All generated attributes fall within archetype ranges
- ✅ Physical correlations (size/speed) work correctly
- ✅ Overall rating calculation uses position-specific weights
- ✅ Attribute generation is deterministic when seeded

---

#### Step 8: Create Name Generator
**File**: `src/player_generation/generators/name_generator.py`

**Implementation**:
```python
import random
from typing import List, Tuple

class NameGenerator:
    """Generates realistic player names."""

    # Position-appropriate name pools
    FIRST_NAMES = [
        "Michael", "Chris", "David", "James", "Robert", "John", "Daniel", "Matthew",
        "Brandon", "Justin", "Tyler", "Ryan", "Josh", "Andrew", "Kevin", "Brian",
        "Marcus", "Darius", "DeAndre", "Jamal", "Lamar", "Antonio", "Terrell",
        "Cameron", "Jordan", "Taylor", "Mason", "Logan", "Ethan", "Noah"
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
        "Harris", "Clark", "Lewis", "Robinson", "Walker", "Allen", "Young", "King"
    ]

    @staticmethod
    def generate_name() -> str:
        """Generate random player name."""
        first = random.choice(NameGenerator.FIRST_NAMES)
        last = random.choice(NameGenerator.LAST_NAMES)
        return f"{first} {last}"

    @staticmethod
    def generate_unique_names(count: int) -> List[str]:
        """Generate list of unique names."""
        names = set()
        attempts = 0
        max_attempts = count * 10

        while len(names) < count and attempts < max_attempts:
            names.add(NameGenerator.generate_name())
            attempts += 1

        return list(names)
```

**Test Cases**:
```python
def test_name_generation():
    """Verify name generation produces valid names."""
    name = NameGenerator.generate_name()
    assert " " in name  # Should have space between first and last
    parts = name.split()
    assert len(parts) == 2
    assert parts[0] in NameGenerator.FIRST_NAMES
    assert parts[1] in NameGenerator.LAST_NAMES

def test_unique_name_generation():
    """Verify unique name generation avoids duplicates."""
    names = NameGenerator.generate_unique_names(50)
    assert len(names) == 50
    assert len(set(names)) == 50  # All unique
```

**Acceptance Criteria**:
- ✅ Names are realistic and properly formatted
- ✅ Unique name generation avoids duplicates
- ✅ Name pools are diverse and representative

---

#### Step 9: Create Core Player Generator
**File**: `src/player_generation/generators/player_generator.py`

**Implementation**:
```python
from typing import Optional
import uuid
from ..models.generated_player import GeneratedPlayer
from ..archetypes.base_archetype import PlayerArchetype
from ..archetypes.archetype_registry import ArchetypeRegistry
from ..core.generation_context import GenerationConfig, GenerationContext
from .attribute_generator import AttributeGenerator
from .name_generator import NameGenerator

class PlayerGenerator:
    """Core player generation engine."""

    def __init__(self, registry: Optional[ArchetypeRegistry] = None):
        self.registry = registry or ArchetypeRegistry()

    def generate_player(
        self,
        config: GenerationConfig,
        archetype: Optional[PlayerArchetype] = None
    ) -> GeneratedPlayer:
        """Generate a single player."""

        # Select archetype if not provided
        if archetype is None:
            if config.archetype_id:
                archetype = self.registry.get_archetype(config.archetype_id)
            elif config.position:
                archetype = self.registry.select_random_archetype(config.position)

            if archetype is None:
                raise ValueError("Could not determine archetype for generation")

        # Generate attributes
        true_ratings = AttributeGenerator.generate_attributes(archetype)

        # Calculate overall
        true_overall = AttributeGenerator.calculate_overall(
            true_ratings,
            archetype.position.value
        )

        # Apply overall constraints from config
        min_overall, max_overall = config.get_overall_range()
        if true_overall < min_overall or true_overall > max_overall:
            # Scale attributes to fit range
            scale_factor = (min_overall + max_overall) / 2 / true_overall
            true_ratings = {k: int(v * scale_factor) for k, v in true_ratings.items()}
            true_overall = AttributeGenerator.calculate_overall(
                true_ratings,
                archetype.position.value
            )

        # Generate name
        name = NameGenerator.generate_name()

        # Generate player ID
        player_id = self._generate_player_id(config)

        # Determine age
        age = config.age or self._get_default_age(config.context)

        # Create player
        player = GeneratedPlayer(
            player_id=player_id,
            name=name,
            position=archetype.position.value,
            age=age,
            true_ratings=true_ratings,
            true_overall=true_overall,
            archetype_id=archetype.archetype_id,
            generation_context=config.context.value,
            draft_round=config.draft_round,
            draft_pick=config.draft_pick
        )

        return player

    def _generate_player_id(self, config: GenerationConfig) -> str:
        """Generate unique player ID."""
        if config.context == GenerationContext.NFL_DRAFT:
            year = config.draft_year or 2025
            pick = config.draft_pick or 0
            return f"DRAFT_{year}_{pick:03d}"
        elif config.context == GenerationContext.UDFA:
            return f"UDFA_{uuid.uuid4().hex[:8]}"
        else:
            return f"GEN_{uuid.uuid4().hex[:8]}"

    def _get_default_age(self, context: GenerationContext) -> int:
        """Get default age based on context."""
        if context == GenerationContext.NFL_DRAFT:
            return random.randint(21, 23)
        elif context == GenerationContext.UDFA:
            return random.randint(22, 24)
        else:
            return random.randint(23, 26)
```

**Test Cases**:
```python
def test_player_generation_with_archetype():
    """Verify player generation with specified archetype."""
    from ..archetypes.base_archetype import PlayerArchetype, Position, AttributeRange
    from ..core.generation_context import GenerationConfig, GenerationContext

    archetype = PlayerArchetype(
        archetype_id="test_qb",
        position=Position.QB,
        name="Test QB",
        description="Test",
        physical_attributes={
            "speed": AttributeRange(70, 85, 77, 5)
        },
        mental_attributes={
            "awareness": AttributeRange(80, 95, 87, 5)
        },
        position_attributes={
            "accuracy": AttributeRange(85, 99, 92, 4)
        },
        overall_range=AttributeRange(75, 92, 83, 6),
        frequency=1.0,
        peak_age_range=(28, 32),
        development_curve="normal"
    )

    config = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        draft_round=1,
        draft_pick=5,
        draft_year=2025
    )

    generator = PlayerGenerator()
    player = generator.generate_player(config, archetype)

    assert player is not None
    assert player.position == "QB"
    assert player.archetype_id == "test_qb"
    assert player.draft_round == 1
    assert player.draft_pick == 5
    assert player.player_id == "DRAFT_2025_005"

def test_player_generation_random_archetype():
    """Verify player generation selects archetype randomly."""
    config = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        position="QB",
        draft_round=3,
        draft_pick=75
    )

    generator = PlayerGenerator()
    player = generator.generate_player(config)

    assert player.position == "QB"
    assert player.archetype_id != ""  # Should have selected an archetype

def test_overall_range_enforcement():
    """Verify overall range is enforced by config."""
    config = GenerationConfig(
        context=GenerationContext.UDFA,  # UDFA caps at 68 overall
        position="QB"
    )

    generator = PlayerGenerator()
    player = generator.generate_player(config)

    assert player.true_overall <= 68  # UDFA ceiling
```

**Acceptance Criteria**:
- ✅ Player generation produces valid GeneratedPlayer objects
- ✅ Archetype selection works (specified or random)
- ✅ Overall range constraints are enforced
- ✅ Player IDs are unique and context-appropriate
- ✅ Default ages are realistic for context

---

#### Step 10: Create Draft Class Generator
**File**: `src/player_generation/generators/draft_class_generator.py`

**Implementation**:
```python
from typing import List
from ..models.generated_player import GeneratedPlayer
from ..core.generation_context import GenerationConfig, GenerationContext
from .player_generator import PlayerGenerator

class DraftClassGenerator:
    """Generates complete NFL draft classes."""

    # NFL draft structure
    ROUNDS = 7
    PICKS_PER_ROUND = 32
    TOTAL_PICKS = ROUNDS * PICKS_PER_ROUND  # 224 picks

    # Position distribution (percentage of each round)
    POSITION_DISTRIBUTION = {
        1: {  # Round 1: Premium positions
            "QB": 0.15, "EDGE": 0.20, "OT": 0.20, "WR": 0.15, "CB": 0.15, "DT": 0.10, "S": 0.05
        },
        2: {  # Round 2
            "QB": 0.10, "RB": 0.10, "WR": 0.15, "OT": 0.15, "EDGE": 0.15, "CB": 0.15, "S": 0.10, "LB": 0.10
        },
        3: {  # Round 3
            "RB": 0.12, "WR": 0.15, "TE": 0.10, "OG": 0.12, "OT": 0.10, "DT": 0.12, "EDGE": 0.10, "LB": 0.12, "CB": 0.07
        },
        # ... rounds 4-7 with more diverse distributions
    }

    def __init__(self, generator: PlayerGenerator):
        self.generator = generator

    def generate_draft_class(
        self,
        year: int
    ) -> List[GeneratedPlayer]:
        """Generate complete draft class."""

        draft_class = []

        pick_number = 1
        for round_num in range(1, self.ROUNDS + 1):
            round_players = self._generate_round(
                round_num=round_num,
                year=year,
                start_pick=pick_number
            )
            draft_class.extend(round_players)
            pick_number += len(round_players)

        return draft_class

    def _generate_round(
        self,
        round_num: int,
        year: int,
        start_pick: int
    ) -> List[GeneratedPlayer]:
        """Generate all players for a single round."""

        players = []
        positions = self._get_round_positions(round_num)

        for i, position in enumerate(positions):
            pick_number = start_pick + i

            config = GenerationConfig(
                context=GenerationContext.NFL_DRAFT,
                position=position,
                draft_round=round_num,
                draft_pick=pick_number,
                draft_year=year
            )

            player = self.generator.generate_player(config)
            players.append(player)

        return players

    def _get_round_positions(self, round_num: int) -> List[str]:
        """Get position distribution for a round."""
        import random

        distribution = self.POSITION_DISTRIBUTION.get(round_num, {})
        if not distribution:
            # Default distribution for later rounds
            distribution = {
                "RB": 0.10, "WR": 0.12, "TE": 0.08, "OL": 0.20,
                "DL": 0.15, "LB": 0.15, "CB": 0.10, "S": 0.10
            }

        positions = []
        for position, percentage in distribution.items():
            count = int(self.PICKS_PER_ROUND * percentage)
            positions.extend([position] * count)

        # Fill remaining slots randomly
        while len(positions) < self.PICKS_PER_ROUND:
            positions.append(random.choice(list(distribution.keys())))

        # Shuffle to randomize pick order
        random.shuffle(positions)
        return positions[:self.PICKS_PER_ROUND]
```

**Test Cases**:
```python
def test_draft_class_size():
    """Verify draft class has correct number of players."""
    from .player_generator import PlayerGenerator

    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    draft_class = class_gen.generate_draft_class(year=2025)

    assert len(draft_class) == 224  # 7 rounds * 32 picks

def test_draft_class_round_distribution():
    """Verify players are distributed across rounds correctly."""
    from .player_generator import PlayerGenerator

    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    draft_class = class_gen.generate_draft_class(year=2025)

    # Check round distribution
    round_counts = {}
    for player in draft_class:
        round_counts[player.draft_round] = round_counts.get(player.draft_round, 0) + 1

    assert len(round_counts) == 7
    for round_num in range(1, 8):
        assert round_counts[round_num] == 32

def test_draft_class_overall_trend():
    """Verify later rounds have lower overall ratings."""
    from .player_generator import PlayerGenerator

    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    draft_class = class_gen.generate_draft_class(year=2025)

    # Calculate average overall by round
    round_averages = {}
    for round_num in range(1, 8):
        round_players = [p for p in draft_class if p.draft_round == round_num]
        avg_overall = sum(p.true_overall for p in round_players) / len(round_players)
        round_averages[round_num] = avg_overall

    # Round 1 should be higher than Round 7
    assert round_averages[1] > round_averages[7]
```

**Acceptance Criteria**:
- ✅ Draft class contains exactly 224 players (7 rounds × 32 picks)
- ✅ Each round has 32 players
- ✅ Position distribution follows realistic NFL patterns
- ✅ Overall ratings decline from early to late rounds
- ✅ All players have unique IDs and proper metadata

---

#### Step 11: Implement Basic Scouting Error
**File**: `src/player_generation/scouting/scouting_engine.py`

**Implementation**:
```python
import random
from typing import Dict, Tuple
from ..models.generated_player import GeneratedPlayer, ScoutingReport

class ScoutingEngine:
    """Applies scouting error to player ratings."""

    @staticmethod
    def apply_scouting_error(
        player: GeneratedPlayer,
        error_margin: int,
        confidence: str = "medium"
    ) -> None:
        """Apply scouting error to player's ratings."""

        # Generate scouted ratings with error
        scouted_ratings = {}
        for attr_name, true_value in player.true_ratings.items():
            error = random.randint(-error_margin, error_margin)
            scouted_value = max(40, min(99, true_value + error))
            scouted_ratings[attr_name] = scouted_value

        player.scouted_ratings = scouted_ratings

        # Calculate scouted overall
        from ..generators.attribute_generator import AttributeGenerator
        player.scouted_overall = AttributeGenerator.calculate_overall(
            scouted_ratings,
            player.position
        )

        # Create scouting report
        player.scouting_report = ScoutingEngine._create_scouting_report(
            player, error_margin, confidence
        )

    @staticmethod
    def _create_scouting_report(
        player: GeneratedPlayer,
        error_margin: int,
        confidence: str
    ) -> ScoutingReport:
        """Create scouting report for player."""

        # Identify strengths (top 3 attributes)
        sorted_attrs = sorted(
            player.true_ratings.items(),
            key=lambda x: x[1],
            reverse=True
        )
        strengths = [f"{attr}: {val}" for attr, val in sorted_attrs[:3]]

        # Identify weaknesses (bottom 3 attributes)
        weaknesses = [f"{attr}: {val}" for attr, val in sorted_attrs[-3:]]

        # Generate comparison (placeholder)
        comparison = "Plays like a prototypical NFL player"

        # Generate scouting grade
        scouting_grade = ScoutingReport.get_grade_from_overall(player.scouted_overall)

        return ScoutingReport(
            scouted_overall=player.scouted_overall,
            true_overall=player.true_overall,
            error_margin=error_margin,
            confidence=confidence,
            strengths=strengths,
            weaknesses=weaknesses,
            comparison=comparison,
            scouting_grade=scouting_grade
        )
```

**Test Cases**:
```python
def test_scouting_error_application():
    """Verify scouting error is applied correctly."""
    from ..models.generated_player import GeneratedPlayer

    player = GeneratedPlayer(
        player_id="TEST_001",
        name="Test Player",
        position="QB",
        age=22,
        true_ratings={"accuracy": 85, "arm_strength": 88, "awareness": 82},
        true_overall=85
    )

    ScoutingEngine.apply_scouting_error(player, error_margin=5, confidence="high")

    # Check scouted ratings exist
    assert len(player.scouted_ratings) == 3

    # Check error is within margin
    for attr in player.true_ratings:
        true_val = player.true_ratings[attr]
        scouted_val = player.scouted_ratings[attr]
        assert abs(true_val - scouted_val) <= 5

def test_scouting_report_creation():
    """Verify scouting report is created."""
    from ..models.generated_player import GeneratedPlayer

    player = GeneratedPlayer(
        player_id="TEST_002",
        name="Test Player 2",
        position="WR",
        age=21,
        true_ratings={"speed": 92, "catching": 88, "route_running": 85},
        true_overall=88
    )

    ScoutingEngine.apply_scouting_error(player, error_margin=7, confidence="medium")

    assert player.scouting_report is not None
    assert player.scouting_report.confidence == "medium"
    assert len(player.scouting_report.strengths) > 0
    assert len(player.scouting_report.weaknesses) > 0
```

**Acceptance Criteria**:
- ✅ Scouting error is applied within specified margin
- ✅ Scouted ratings stay within valid bounds (40-99)
- ✅ Scouting report identifies strengths and weaknesses
- ✅ Scouting grade matches scouted overall rating
- ✅ Error margin scales with confidence level

---

#### Step 12: Create Integration with Player Class
**File**: `src/player_generation/integration/player_converter.py`

**Implementation**:
```python
from typing import Dict
from ...team_management.players.player import Player
from ..models.generated_player import GeneratedPlayer

class PlayerConverter:
    """Converts GeneratedPlayer to Player class."""

    @staticmethod
    def to_player(generated: GeneratedPlayer, team_id: int = None) -> Player:
        """Convert GeneratedPlayer to Player object."""

        # Use scouted ratings if available for initial creation
        ratings = generated.scouted_ratings if generated.scouted_ratings else generated.true_ratings

        player = Player(
            name=generated.name,
            number=generated.jersey_number or PlayerConverter._get_default_number(generated.position),
            primary_position=generated.position,
            ratings=ratings,
            team_id=team_id
        )

        # Add additional metadata if Player class supports it
        if hasattr(player, 'age'):
            player.age = generated.age
        if hasattr(player, 'traits'):
            player.traits = generated.traits

        return player

    @staticmethod
    def to_player_dict(generated: GeneratedPlayer, team_id: int = None) -> Dict:
        """Convert GeneratedPlayer to Player-compatible dictionary."""

        ratings = generated.scouted_ratings if generated.scouted_ratings else generated.true_ratings

        player_dict = {
            "name": generated.name,
            "number": generated.jersey_number or PlayerConverter._get_default_number(generated.position),
            "primary_position": generated.position,
            "ratings": ratings,
            "team_id": team_id,
            "age": generated.age,
            "traits": generated.traits
        }

        # Add draft metadata if available
        if generated.draft_round:
            player_dict["draft_info"] = {
                "round": generated.draft_round,
                "pick": generated.draft_pick,
                "year": generated.draft_class_id
            }

        return player_dict

    @staticmethod
    def _get_default_number(position: str) -> int:
        """Get default jersey number for position."""
        import random

        number_ranges = {
            "QB": (1, 19),
            "RB": (20, 49),
            "WR": (10, 19),
            "TE": (40, 49),
            "OL": (50, 79),
            "DL": (50, 99),
            "LB": (40, 59),
            "CB": (20, 49),
            "S": (20, 49),
            "K": (1, 19),
            "P": (1, 19)
        }

        min_num, max_num = number_ranges.get(position, (1, 99))
        return random.randint(min_num, max_num)
```

**Test Cases**:
```python
def test_player_conversion():
    """Verify GeneratedPlayer converts to Player correctly."""
    from ..models.generated_player import GeneratedPlayer
    from ...team_management.players.player import Player

    generated = GeneratedPlayer(
        player_id="TEST_001",
        name="John Smith",
        position="QB",
        age=22,
        jersey_number=12,
        true_ratings={"accuracy": 85, "arm_strength": 88},
        scouted_ratings={"accuracy": 82, "arm_strength": 90},
        true_overall=86,
        scouted_overall=85
    )

    player = PlayerConverter.to_player(generated, team_id=14)

    assert isinstance(player, Player)
    assert player.name == "John Smith"
    assert player.number == 12
    assert player.primary_position == "QB"
    assert player.team_id == 14
    # Uses scouted ratings
    assert player.ratings["arm_strength"] == 90

def test_player_dict_conversion():
    """Verify conversion to dictionary format."""
    from ..models.generated_player import GeneratedPlayer

    generated = GeneratedPlayer(
        player_id="DRAFT_2025_015",
        name="Test Player",
        position="WR",
        age=21,
        true_ratings={"speed": 90},
        draft_round=1,
        draft_pick=15,
        draft_class_id="draft_class_2025"
    )

    player_dict = PlayerConverter.to_player_dict(generated, team_id=9)

    assert player_dict["name"] == "Test Player"
    assert player_dict["team_id"] == 9
    assert "draft_info" in player_dict
    assert player_dict["draft_info"]["round"] == 1
```

**Acceptance Criteria**:
- ✅ GeneratedPlayer converts to Player class correctly
- ✅ Scouted ratings are used for initial creation
- ✅ Draft metadata is preserved in conversion
- ✅ Default jersey numbers follow NFL position rules
- ✅ Dictionary conversion maintains all necessary data

---

### Sprint 2 Completion Summary

**Status**: ✅ **COMPLETE** (October 5, 2025)

**Implemented Components**:
1. ✅ Attribute Generator (`src/player_generation/generators/attribute_generator.py`)
2. ✅ Name Generator (`src/player_generation/generators/name_generator.py`)
3. ✅ Player Generator (`src/player_generation/generators/player_generator.py`)
4. ✅ Draft Class Generator (`src/player_generation/generators/draft_class_generator.py`)

**Test Results**:
- **Total Tests**: 6 tests (all passing)
- **Test Status**: ✅ All tests verified and passing
- **Test File**: `tests/player_generation/test_sprint2.py`
- **Coverage**: All 4 generator components tested with multiple scenarios
- **Test Execution**: Successfully executed with PYTHONPATH=src

**Key Achievements**:
- Complete generator module created under `src/player_generation/generators/`
- Attribute generation respects archetype ranges and correlations
- Position-weighted overall calculation implemented for all NFL positions
- Name generator creates realistic, unique player names
- Player ID generation contextual (DRAFT_YYYY_XXX, UDFA_XXXX, GEN_XXXX)
- Overall range enforcement from generation context working correctly
- Draft class generator produces complete 7-round, 224-player draft classes
- Position distribution per round realistic and NFL-accurate
- Round-based overall trending (Round 1 > Round 7) verified

**Next Steps**:
- Proceed to Sprint 3 for archetype JSON configuration files
- Create realistic archetypes for all 14 NFL positions
- Define multiple archetypes per position for diversity

---

### Sprint 3: Archetype System Foundation
**Duration**: 4-5 days
**Goal**: Create comprehensive archetype library for QB, RB, WR, TE

#### Step 13-18: Create Position-Specific Archetypes
**Files**: `src/config/archetypes/qb_archetypes.json`, `rb_archetypes.json`, etc.

I'll show one complete example:

**Step 13: Create QB Archetypes**
**File**: `src/config/archetypes/qb_archetypes.json`

**Implementation**:
```json
[
  {
    "archetype_id": "pocket_passer_qb",
    "position": "QB",
    "name": "Pocket Passer",
    "description": "Traditional pocket quarterback with elite accuracy and decision-making",
    "physical_attributes": {
      "speed": {"min": 65, "max": 80, "mean": 72, "std_dev": 5},
      "strength": {"min": 70, "max": 85, "mean": 77, "std_dev": 5},
      "agility": {"min": 70, "max": 85, "mean": 77, "std_dev": 5}
    },
    "mental_attributes": {
      "awareness": {"min": 80, "max": 99, "mean": 90, "std_dev": 5},
      "intelligence": {"min": 75, "max": 95, "mean": 85, "std_dev": 5}
    },
    "position_attributes": {
      "accuracy": {"min": 85, "max": 99, "mean": 92, "std_dev": 4},
      "arm_strength": {"min": 75, "max": 92, "mean": 83, "std_dev": 6},
      "release": {"min": 80, "max": 95, "mean": 87, "std_dev": 5}
    },
    "overall_range": {"min": 75, "max": 95, "mean": 85, "std_dev": 6},
    "frequency": 0.30,
    "peak_age_range": [28, 32],
    "development_curve": "normal"
  },
  {
    "archetype_id": "mobile_qb",
    "position": "QB",
    "name": "Mobile QB",
    "description": "Athletic quarterback who can beat defenses with legs and arm",
    "physical_attributes": {
      "speed": {"min": 82, "max": 95, "mean": 88, "std_dev": 4},
      "strength": {"min": 65, "max": 80, "mean": 72, "std_dev": 5},
      "agility": {"min": 80, "max": 95, "mean": 87, "std_dev": 5}
    },
    "mental_attributes": {
      "awareness": {"min": 70, "max": 88, "mean": 79, "std_dev": 6},
      "intelligence": {"min": 70, "max": 85, "mean": 77, "std_dev": 5}
    },
    "position_attributes": {
      "accuracy": {"min": 75, "max": 90, "mean": 82, "std_dev": 5},
      "arm_strength": {"min": 78, "max": 92, "mean": 85, "std_dev": 5},
      "release": {"min": 75, "max": 88, "mean": 81, "std_dev": 4}
    },
    "overall_range": {"min": 72, "max": 92, "mean": 82, "std_dev": 6},
    "frequency": 0.25,
    "peak_age_range": [25, 29],
    "development_curve": "early"
  },
  {
    "archetype_id": "dual_threat_qb",
    "position": "QB",
    "name": "Dual-Threat QB",
    "description": "Balanced quarterback equally dangerous passing and rushing",
    "physical_attributes": {
      "speed": {"min": 85, "max": 96, "mean": 90, "std_dev": 4},
      "strength": {"min": 70, "max": 85, "mean": 77, "std_dev": 5},
      "agility": {"min": 82, "max": 95, "mean": 88, "std_dev": 4}
    },
    "mental_attributes": {
      "awareness": {"min": 75, "max": 92, "mean": 83, "std_dev": 5},
      "intelligence": {"min": 72, "max": 88, "mean": 80, "std_dev": 5}
    },
    "position_attributes": {
      "accuracy": {"min": 78, "max": 93, "mean": 85, "std_dev": 5},
      "arm_strength": {"min": 80, "max": 94, "mean": 87, "std_dev": 5},
      "release": {"min": 78, "max": 90, "mean": 84, "std_dev": 4}
    },
    "overall_range": {"min": 75, "max": 94, "mean": 84, "std_dev": 6},
    "frequency": 0.20,
    "peak_age_range": [26, 30],
    "development_curve": "normal"
  },
  {
    "archetype_id": "game_manager_qb",
    "position": "QB",
    "name": "Game Manager",
    "description": "Smart, efficient quarterback who limits mistakes",
    "physical_attributes": {
      "speed": {"min": 60, "max": 75, "mean": 67, "std_dev": 5},
      "strength": {"min": 65, "max": 80, "mean": 72, "std_dev": 5},
      "agility": {"min": 65, "max": 78, "mean": 71, "std_dev": 4}
    },
    "mental_attributes": {
      "awareness": {"min": 82, "max": 96, "mean": 89, "std_dev": 4},
      "intelligence": {"min": 80, "max": 95, "mean": 87, "std_dev": 5}
    },
    "position_attributes": {
      "accuracy": {"min": 80, "max": 92, "mean": 86, "std_dev": 4},
      "arm_strength": {"min": 68, "max": 82, "mean": 75, "std_dev": 5},
      "release": {"min": 78, "max": 90, "mean": 84, "std_dev": 4}
    },
    "overall_range": {"min": 68, "max": 85, "mean": 76, "std_dev": 5},
    "frequency": 0.15,
    "peak_age_range": [27, 33],
    "development_curve": "late"
  },
  {
    "archetype_id": "gunslinger_qb",
    "position": "QB",
    "name": "Gunslinger",
    "description": "High-risk, high-reward quarterback with cannon arm",
    "physical_attributes": {
      "speed": {"min": 68, "max": 82, "mean": 75, "std_dev": 5},
      "strength": {"min": 75, "max": 88, "mean": 81, "std_dev": 5},
      "agility": {"min": 70, "max": 83, "mean": 76, "std_dev": 4}
    },
    "mental_attributes": {
      "awareness": {"min": 65, "max": 82, "mean": 73, "std_dev": 6},
      "intelligence": {"min": 68, "max": 82, "mean": 75, "std_dev": 5}
    },
    "position_attributes": {
      "accuracy": {"min": 70, "max": 88, "mean": 79, "std_dev": 6},
      "arm_strength": {"min": 88, "max": 99, "mean": 93, "std_dev": 4},
      "release": {"min": 80, "max": 92, "mean": 86, "std_dev": 4}
    },
    "overall_range": {"min": 70, "max": 90, "mean": 80, "std_dev": 6},
    "frequency": 0.10,
    "peak_age_range": [26, 31],
    "development_curve": "normal"
  }
]
```

**Test Cases**:
```python
def test_qb_archetype_loading():
    """Verify QB archetypes load correctly from JSON."""
    from ..archetypes.archetype_registry import ArchetypeRegistry

    registry = ArchetypeRegistry(config_dir="src/config/archetypes/")
    qb_archetypes = registry.get_archetypes_by_position("QB")

    assert len(qb_archetypes) >= 5  # Should have at least 5 QB archetypes

    # Check specific archetypes exist
    archetype_ids = [a.archetype_id for a in qb_archetypes]
    assert "pocket_passer_qb" in archetype_ids
    assert "mobile_qb" in archetype_ids
    assert "dual_threat_qb" in archetype_ids

def test_qb_archetype_frequency_distribution():
    """Verify QB archetypes have realistic frequency distribution."""
    from ..archetypes.archetype_registry import ArchetypeRegistry

    registry = ArchetypeRegistry(config_dir="src/config/archetypes/")
    qb_archetypes = registry.get_archetypes_by_position("QB")

    # Total frequency should be close to 1.0
    total_freq = sum(a.frequency for a in qb_archetypes)
    assert 0.95 <= total_freq <= 1.05
```

**Acceptance Criteria**:
- ✅ 5+ QB archetypes with distinct characteristics
- ✅ Total frequency across archetypes ≈ 1.0
- ✅ Attribute ranges are realistic for each archetype
- ✅ Peak ages reflect real NFL trends
- ✅ JSON validates against archetype schema

**Note**: Steps 14-18 follow identical pattern for RB, WR, TE, OL positions with 4-6 archetypes each.

---

### Sprint 4: Complete Archetype Library
**Duration**: 5-6 days
**Goal**: Create archetypes for all defensive positions and special teams

#### Step 19-24: Create Defensive and Special Teams Archetypes

**Files**:
- `src/config/archetypes/edge_archetypes.json`
- `src/config/archetypes/dt_archetypes.json`
- `src/config/archetypes/lb_archetypes.json`
- `src/config/archetypes/cb_archetypes.json`
- `src/config/archetypes/s_archetypes.json`
- `src/config/archetypes/st_archetypes.json` (K, P, LS)

**Example - EDGE Archetypes** (Step 19):
```json
[
  {
    "archetype_id": "speed_rusher_edge",
    "position": "EDGE",
    "name": "Speed Rusher",
    "description": "Elite speed rusher who beats tackles around the edge",
    "physical_attributes": {
      "speed": {"min": 85, "max": 97, "mean": 91, "std_dev": 4},
      "strength": {"min": 70, "max": 85, "mean": 77, "std_dev": 5},
      "agility": {"min": 82, "max": 95, "mean": 88, "std_dev": 4}
    },
    "mental_attributes": {
      "awareness": {"min": 72, "max": 88, "mean": 80, "std_dev": 5},
      "play_recognition": {"min": 70, "max": 85, "mean": 77, "std_dev": 5}
    },
    "position_attributes": {
      "pass_rush": {"min": 82, "max": 96, "mean": 89, "std_dev": 5},
      "run_defense": {"min": 65, "max": 80, "mean": 72, "std_dev": 5},
      "block_shedding": {"min": 70, "max": 85, "mean": 77, "std_dev": 5}
    },
    "overall_range": {"min": 73, "max": 93, "mean": 83, "std_dev": 6},
    "frequency": 0.35,
    "peak_age_range": [26, 30],
    "development_curve": "normal"
  },
  {
    "archetype_id": "power_rusher_edge",
    "position": "EDGE",
    "name": "Power Rusher",
    "description": "Physical edge rusher who overpowers offensive linemen",
    "physical_attributes": {
      "speed": {"min": 75, "max": 88, "mean": 81, "std_dev": 5},
      "strength": {"min": 85, "max": 97, "mean": 91, "std_dev": 4},
      "agility": {"min": 72, "max": 85, "mean": 78, "std_dev": 4}
    },
    "mental_attributes": {
      "awareness": {"min": 70, "max": 86, "mean": 78, "std_dev": 5},
      "play_recognition": {"min": 68, "max": 82, "mean": 75, "std_dev": 5}
    },
    "position_attributes": {
      "pass_rush": {"min": 78, "max": 92, "mean": 85, "std_dev": 5},
      "run_defense": {"min": 75, "max": 90, "mean": 82, "std_dev": 5},
      "block_shedding": {"min": 80, "max": 94, "mean": 87, "std_dev": 5}
    },
    "overall_range": {"min": 72, "max": 91, "mean": 81, "std_dev": 6},
    "frequency": 0.30,
    "peak_age_range": [25, 29],
    "development_curve": "early"
  }
  // ... 3-4 more EDGE archetypes
]
```

**Test Cases** (for each position):
```python
def test_defensive_archetype_coverage():
    """Verify all defensive positions have archetypes."""
    from ..archetypes.archetype_registry import ArchetypeRegistry

    registry = ArchetypeRegistry(config_dir="src/config/archetypes/")

    defensive_positions = ["EDGE", "DT", "LB", "CB", "S"]
    for position in defensive_positions:
        archetypes = registry.get_archetypes_by_position(position)
        assert len(archetypes) >= 3, f"Missing archetypes for {position}"

def test_total_archetype_count():
    """Verify comprehensive archetype library."""
    from ..archetypes.archetype_registry import ArchetypeRegistry

    registry = ArchetypeRegistry(config_dir="src/config/archetypes/")

    # Should have 30+ total archetypes across all positions
    assert registry.get_archetype_count() >= 30
```

**Acceptance Criteria (Steps 19-24)**:
- ✅ 3-5 archetypes per defensive position (EDGE, DT, LB, CB, S)
- ✅ 1-2 archetypes for special teams (K, P, LS)
- ✅ 30+ total archetypes across all positions
- ✅ All archetypes pass validation
- ✅ Position-specific attributes are realistic

---

### Sprint 5: Draft Class Generation
**Duration**: 4-5 days
**Goal**: Implement complete draft class generation with talent variation

#### Step 25: Implement Talent Class Variation
**File**: `src/player_generation/generators/talent_class_generator.py`

**Implementation**:
```python
from enum import Enum
import random
from typing import Dict

class DraftClassTalentLevel(Enum):
    """Overall talent level of draft class."""
    WEAK = "weak"
    BELOW_AVERAGE = "below_average"
    AVERAGE = "average"
    ABOVE_AVERAGE = "above_average"
    ELITE = "elite"

class TalentClassGenerator:
    """Determines overall talent level of draft class."""

    # Frequency of each talent level
    TALENT_FREQUENCIES = {
        DraftClassTalentLevel.WEAK: 0.10,
        DraftClassTalentLevel.BELOW_AVERAGE: 0.20,
        DraftClassTalentLevel.AVERAGE: 0.40,
        DraftClassTalentLevel.ABOVE_AVERAGE: 0.20,
        DraftClassTalentLevel.ELITE: 0.10
    }

    # Overall modifiers for each talent level
    TALENT_MODIFIERS = {
        DraftClassTalentLevel.WEAK: -5,
        DraftClassTalentLevel.BELOW_AVERAGE: -2,
        DraftClassTalentLevel.AVERAGE: 0,
        DraftClassTalentLevel.ABOVE_AVERAGE: +2,
        DraftClassTalentLevel.ELITE: +5
    }

    @staticmethod
    def determine_class_talent() -> DraftClassTalentLevel:
        """Randomly determine draft class talent level."""
        levels = list(TalentClassGenerator.TALENT_FREQUENCIES.keys())
        weights = list(TalentClassGenerator.TALENT_FREQUENCIES.values())
        return random.choices(levels, weights=weights)[0]

    @staticmethod
    def get_talent_modifier(talent_level: DraftClassTalentLevel) -> int:
        """Get overall modifier for talent level."""
        return TalentClassGenerator.TALENT_MODIFIERS[talent_level]

    @staticmethod
    def apply_class_talent_to_config(
        config: 'GenerationConfig',
        talent_level: DraftClassTalentLevel
    ) -> 'GenerationConfig':
        """Apply talent modifier to generation config."""
        modifier = TalentClassGenerator.get_talent_modifier(talent_level)

        # Adjust overall range
        min_overall, max_overall = config.get_overall_range()
        config.overall_min = max(40, min_overall + modifier)
        config.overall_max = min(99, max_overall + modifier)

        return config
```

**Test Cases**:
```python
def test_talent_level_distribution():
    """Verify talent level frequency distribution."""
    levels = [TalentClassGenerator.determine_class_talent() for _ in range(1000)]

    # Average should be most common
    avg_count = levels.count(DraftClassTalentLevel.AVERAGE)
    weak_count = levels.count(DraftClassTalentLevel.WEAK)
    elite_count = levels.count(DraftClassTalentLevel.ELITE)

    assert avg_count > weak_count
    assert avg_count > elite_count

def test_talent_modifier_application():
    """Verify talent modifiers adjust overall ranges correctly."""
    from ..core.generation_context import GenerationConfig, GenerationContext

    config = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        draft_round=1
    )

    # Elite class should increase overall range
    elite_config = TalentClassGenerator.apply_class_talent_to_config(
        config,
        DraftClassTalentLevel.ELITE
    )

    assert elite_config.overall_min > config.overall_min
    assert elite_config.overall_max > config.overall_max
```

**Acceptance Criteria**:
- ✅ Talent levels follow realistic frequency distribution
- ✅ Modifiers appropriately adjust overall ranges
- ✅ Weak classes produce lower-rated players
- ✅ Elite classes produce higher-rated players
- ✅ Average classes remain unchanged

---

#### Step 26: Implement Position Scarcity
**File**: `src/player_generation/generators/position_scarcity.py`

**Implementation**:
```python
from enum import Enum
from typing import Dict

class PositionScarcity(Enum):
    """NFL position scarcity/value tiers."""
    PREMIUM = "premium"  # QB, OT, EDGE, CB
    HIGH_VALUE = "high_value"  # WR, DT, S
    MEDIUM_VALUE = "medium_value"  # RB, TE, LB, OG
    LOW_VALUE = "low_value"  # C, K, P, LS

class PositionScarcityManager:
    """Manages position scarcity in draft class generation."""

    SCARCITY_TIERS = {
        "QB": PositionScarcity.PREMIUM,
        "OT": PositionScarcity.PREMIUM,
        "EDGE": PositionScarcity.PREMIUM,
        "CB": PositionScarcity.PREMIUM,
        "WR": PositionScarcity.HIGH_VALUE,
        "DT": PositionScarcity.HIGH_VALUE,
        "S": PositionScarcity.HIGH_VALUE,
        "RB": PositionScarcity.MEDIUM_VALUE,
        "TE": PositionScarcity.MEDIUM_VALUE,
        "LB": PositionScarcity.MEDIUM_VALUE,
        "OG": PositionScarcity.MEDIUM_VALUE,
        "C": PositionScarcity.LOW_VALUE,
        "K": PositionScarcity.LOW_VALUE,
        "P": PositionScarcity.LOW_VALUE
    }

    # Quality caps by scarcity tier (max number of elite players)
    ELITE_CAPS = {
        PositionScarcity.PREMIUM: 3,  # Up to 3 elite QBs per class
        PositionScarcity.HIGH_VALUE: 5,
        PositionScarcity.MEDIUM_VALUE: 4,
        PositionScarcity.LOW_VALUE: 1
    }

    @staticmethod
    def get_position_scarcity(position: str) -> PositionScarcity:
        """Get scarcity tier for position."""
        return PositionScarcityManager.SCARCITY_TIERS.get(
            position,
            PositionScarcity.MEDIUM_VALUE
        )

    @staticmethod
    def should_limit_elite_player(position: str, elite_count: int) -> bool:
        """Determine if another elite player at position should be limited."""
        scarcity = PositionScarcityManager.get_position_scarcity(position)
        cap = PositionScarcityManager.ELITE_CAPS[scarcity]
        return elite_count >= cap

    @staticmethod
    def adjust_for_scarcity(
        overall: int,
        position: str,
        elite_count: Dict[str, int]
    ) -> int:
        """Adjust overall based on position scarcity limits."""

        if overall >= 85:  # Elite threshold
            current_count = elite_count.get(position, 0)
            if PositionScarcityManager.should_limit_elite_player(position, current_count):
                # Reduce to high-quality but not elite
                return random.randint(78, 84)

        return overall
```

**Test Cases**:
```python
def test_position_scarcity_tiers():
    """Verify premium positions have correct scarcity."""
    assert PositionScarcityManager.get_position_scarcity("QB") == PositionScarcity.PREMIUM
    assert PositionScarcityManager.get_position_scarcity("EDGE") == PositionScarcity.PREMIUM
    assert PositionScarcityManager.get_position_scarcity("RB") == PositionScarcity.MEDIUM_VALUE

def test_elite_player_limiting():
    """Verify elite players are limited by position scarcity."""
    elite_count = {"QB": 3}  # Already at QB elite cap

    # Should limit new elite QB
    assert PositionScarcityManager.should_limit_elite_player("QB", 3)

    # Should not limit new elite WR
    assert not PositionScarcityManager.should_limit_elite_player("WR", 3)
```

**Acceptance Criteria**:
- ✅ Position scarcity tiers defined for all positions
- ✅ Elite player caps prevent unrealistic draft classes
- ✅ Premium positions (QB, OT) have stricter limits
- ✅ Scarcity adjustments preserve overall realism

---

#### Step 27: Enhance Draft Class Generator with Variation
**File**: Update `src/player_generation/generators/draft_class_generator.py`

**Implementation** (additions to existing class):
```python
class DraftClassGenerator:
    # ... existing code ...

    def generate_draft_class_with_variation(
        self,
        year: int,
        talent_level: DraftClassTalentLevel = None
    ) -> List[GeneratedPlayer]:
        """Generate draft class with talent variation and position scarcity."""

        # Determine talent level if not specified
        if talent_level is None:
            talent_level = TalentClassGenerator.determine_class_talent()

        draft_class = []
        elite_count = {}  # Track elite players by position

        talent_modifier = TalentClassGenerator.get_talent_modifier(talent_level)

        pick_number = 1
        for round_num in range(1, self.ROUNDS + 1):
            round_players = self._generate_round_with_variation(
                round_num=round_num,
                year=year,
                start_pick=pick_number,
                talent_modifier=talent_modifier,
                elite_count=elite_count
            )
            draft_class.extend(round_players)
            pick_number += len(round_players)

        return draft_class

    def _generate_round_with_variation(
        self,
        round_num: int,
        year: int,
        start_pick: int,
        talent_modifier: int,
        elite_count: Dict[str, int]
    ) -> List[GeneratedPlayer]:
        """Generate round with talent and scarcity adjustments."""

        players = []
        positions = self._get_round_positions(round_num)

        for i, position in enumerate(positions):
            pick_number = start_pick + i

            config = GenerationConfig(
                context=GenerationContext.NFL_DRAFT,
                position=position,
                draft_round=round_num,
                draft_pick=pick_number,
                draft_year=year
            )

            # Apply talent modifier
            min_overall, max_overall = config.get_overall_range()
            config.overall_min = max(40, min_overall + talent_modifier)
            config.overall_max = min(99, max_overall + talent_modifier)

            player = self.generator.generate_player(config)

            # Apply position scarcity
            adjusted_overall = PositionScarcityManager.adjust_for_scarcity(
                player.true_overall,
                position,
                elite_count
            )

            if adjusted_overall != player.true_overall:
                # Re-scale attributes
                scale_factor = adjusted_overall / player.true_overall
                player.true_ratings = {
                    k: int(v * scale_factor)
                    for k, v in player.true_ratings.items()
                }
                player.true_overall = adjusted_overall

            # Track elite players
            if player.true_overall >= 85:
                elite_count[position] = elite_count.get(position, 0) + 1

            players.append(player)

        return players
```

**Test Cases**:
```python
def test_draft_class_talent_variation():
    """Verify draft class respects talent level modifiers."""
    from .player_generator import PlayerGenerator
    from .talent_class_generator import DraftClassTalentLevel

    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    # Generate elite class
    elite_class = class_gen.generate_draft_class_with_variation(
        year=2025,
        talent_level=DraftClassTalentLevel.ELITE
    )

    # Generate weak class
    weak_class = class_gen.generate_draft_class_with_variation(
        year=2026,
        talent_level=DraftClassTalentLevel.WEAK
    )

    # Elite class should have higher average overall
    elite_avg = sum(p.true_overall for p in elite_class) / len(elite_class)
    weak_avg = sum(p.true_overall for p in weak_class) / len(weak_class)
    assert elite_avg > weak_avg

def test_position_scarcity_in_draft_class():
    """Verify position scarcity limits elite players."""
    from .player_generator import PlayerGenerator

    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    draft_class = class_gen.generate_draft_class_with_variation(year=2025)

    # Count elite QBs (should be ≤ 3)
    elite_qbs = [p for p in draft_class if p.position == "QB" and p.true_overall >= 85]
    assert len(elite_qbs) <= 3
```

**Acceptance Criteria**:
- ✅ Draft classes vary realistically between weak and elite
- ✅ Position scarcity prevents too many elite players at premium positions
- ✅ Talent modifiers affect overall class quality
- ✅ Elite player counts respect position-specific caps

---

#### Step 28-30: Draft Class Testing and Validation

**Step 28: Statistical Validation Tests**
**File**: `tests/player_generation/test_draft_class_statistics.py`

**Test Cases**:
```python
def test_draft_class_overall_distribution():
    """Verify overall ratings follow expected distribution."""
    from src.player_generation.generators.player_generator import PlayerGenerator
    from src.player_generation.generators.draft_class_generator import DraftClassGenerator

    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    draft_class = class_gen.generate_draft_class_with_variation(year=2025)
    overalls = [p.true_overall for p in draft_class]

    # Check distribution properties
    import numpy as np
    mean = np.mean(overalls)
    std = np.std(overalls)

    # Draft class mean should be 65-75
    assert 65 <= mean <= 75

    # Should have reasonable spread
    assert 8 <= std <= 15

    # Check for outliers (elite and busts)
    elite = [o for o in overalls if o >= 85]
    busts = [o for o in overalls if o < 55]

    assert 5 <= len(elite) <= 25  # Some elite talent
    assert len(busts) <= 30  # Some busts but not too many

def test_position_distribution_balance():
    """Verify position distribution is balanced."""
    from src.player_generation.generators.player_generator import PlayerGenerator
    from src.player_generation.generators.draft_class_generator import DraftClassGenerator

    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    draft_class = class_gen.generate_draft_class_with_variation(year=2025)

    # Count by position
    position_counts = {}
    for player in draft_class:
        position_counts[player.position] = position_counts.get(player.position, 0) + 1

    # Key positions should have reasonable representation
    assert position_counts.get("QB", 0) >= 10  # At least 10 QBs
    assert position_counts.get("WR", 0) >= 20  # At least 20 WRs
    assert position_counts.get("OL", 0) >= 35  # At least 35 OL combined
```

**Acceptance Criteria**:
- ✅ Overall distribution matches realistic NFL draft patterns
- ✅ Position distribution is balanced and realistic
- ✅ Class has appropriate mix of elite, average, and bust players
- ✅ Statistical tests pass with p-value > 0.05

---

### Sprint 6: Scouting System
**Duration**: 4-5 days
**Goal**: Implement comprehensive scouting with confidence levels and grades

*(Steps 31-36 continue with scouting improvements, NFL comparisons, scouting reports...)*

---

### Sprint 7: Development Curves
**Duration**: 4-5 days
**Goal**: Implement age-based player development

*(Steps 37-42 cover development profiles, growth/decline rates, injury risk...)*

---

### Sprint 8: Traits & Names
**Duration**: 3-4 days
**Goal**: Add traits and enhanced name generation

*(Steps 43-48 cover trait system, name pools, nickname generation...)*

---

### Sprint 9: College & Background
**Duration**: 3-4 days
**Goal**: Add college and background information

*(Steps 49-54 cover college generation, combine stats, production metrics...)*

---

### Sprint 10: Advanced Features
**Duration**: 2-3 days
**Goal**: Add UDFA and international player generation

*(Steps 55-56 cover UDFA pools, international leagues...)*

---

## Testing Strategy

### Unit Testing
- **Distributions**: Verify statistical properties (mean, std dev, bounds)
- **Correlations**: Test attribute relationships
- **Archetypes**: Validate configurations and constraints
- **Generators**: Test player generation logic

### Integration Testing
- **Draft Classes**: Generate complete classes and validate
- **Event System**: Test DraftPickEvent integration
- **Database**: Verify persistence and retrieval
- **Contract System**: Test rookie contract creation

### Statistical Testing
- **Distribution Validation**: Chi-square tests for attribute distributions
- **Archetype Frequency**: Verify weighted selection follows expected probabilities
- **Class Variation**: Confirm talent levels produce different outcomes
- **Position Scarcity**: Validate elite player caps work correctly

### Performance Testing
- **Generation Speed**: 262-player draft class in <5 seconds
- **Memory Usage**: Monitor during large batch generation
- **Database I/O**: Optimize persistence operations

---

## Integration Points

### Player Class Conversion
- Clean conversion from GeneratedPlayer to existing Player class
- Preservation of all attribute ratings and metadata
- Support for scouted vs true ratings display

---

## Risk Assessment

### Technical Risks

**Risk 1**: Statistical distributions don't match NFL reality
- **Mitigation**: Extensive validation against real NFL data
- **Fallback**: Tunable parameters in JSON configuration

**Risk 2**: Performance issues with large batch generation
- **Mitigation**: Profile and optimize critical paths early
- **Fallback**: Implement async generation for UI responsiveness

**Risk 3**: Archetype configurations become unmaintainable
- **Mitigation**: JSON schema validation and editor tooling
- **Fallback**: Reduce archetype count to essential templates

### Design Risks

**Risk 1**: Generated players feel "samey" or unrealistic
- **Mitigation**: Add trait system and background variation
- **Fallback**: Increase randomness in attribute generation

**Risk 2**: Scouting system too complex for users
- **Mitigation**: Provide multiple difficulty levels
- **Fallback**: Simplify to basic error margin only

---

## Timeline & Milestones

### Phase 1: Foundation (Weeks 1-2)
- **Week 1**: Sprints 1-2 (Core Infrastructure + Basic Generation)
  - Milestone: Generate single players with archetypes
- **Week 2**: Sprints 3-4 (Archetype Library)
  - Milestone: 30+ archetypes across all positions

### Phase 2: Draft Classes (Weeks 3-4)
- **Week 3**: Sprint 5 (Draft Class Generation)
  - Milestone: Generate complete 262-player draft classes
- **Week 4**: Sprint 6 (Scouting System)
  - Milestone: Scouting reports with confidence levels

### Phase 3: Advanced Features (Weeks 5-6)
- **Week 5**: Sprints 7-8 (Development + Traits)
  - Milestone: Age-based development curves
- **Week 6**: Sprints 9-10 (Background + Advanced Features)
  - Milestone: College backgrounds, UDFA, international players

### Final Deliverables (Week 6)
- ✅ 30+ position-specific archetypes
- ✅ Complete draft class generator (262 players)
- ✅ Scouting system with error and confidence
- ✅ Development curves and aging
- ✅ Trait and background systems
- ✅ UDFA and international player support
- ✅ Player class conversion support
- ✅ Comprehensive test suite (>80% coverage)
- ✅ Documentation and API reference

---

## Success Metrics

### Functional Metrics
- ✅ Generate 262-player draft class in <5 seconds
- ✅ 30+ archetypes with 100% validation pass rate
- ✅ Scouting error ±10 points on average from true ratings
- ✅ Position scarcity caps prevent unrealistic classes
- ✅ Development curves produce realistic career arcs

### Quality Metrics
- ✅ >80% test coverage on core generation logic
- ✅ Generated players "feel real" to NFL observers
- ✅ Attribute distributions match NFL statistical profiles
- ✅ Draft class variation produces weak/average/elite classes
- ✅ Zero crashes or data corruption in generation pipeline
- ✅ 100% compatibility with existing Player class

---

## Appendix: Code Examples

### Basic Usage

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.core.generation_context import GenerationConfig, GenerationContext

# Generate single draft prospect
generator = PlayerGenerator()
config = GenerationConfig(
    context=GenerationContext.NFL_DRAFT,
    position="QB",
    draft_round=1,
    draft_pick=5,
    draft_year=2025
)

player = generator.generate_player(config)
print(f"{player.name} - {player.position} - Overall: {player.true_overall}")
```

### Generate Complete Draft Class

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.generators.draft_class_generator import DraftClassGenerator

generator = PlayerGenerator()
class_gen = DraftClassGenerator(generator)

draft_class = class_gen.generate_draft_class_with_variation(
    year=2025
)

print(f"Generated {len(draft_class)} players")
for player in draft_class[:10]:  # Show first 10 picks
    print(f"Pick {player.draft_pick}: {player.name} ({player.position}) - {player.true_overall} OVR")
```

### Integration with Draft Event

```python
from events.draft_events import DraftPickEvent
from player_generation.integration.player_converter import PlayerConverter

# Generate player
player = generator.generate_player(config)

# Convert to Player class
nfl_player = PlayerConverter.to_player(player, team_id=14)

# Create draft event
draft_event = DraftPickEvent(
    team_id=14,
    round_number=player.draft_round,
    pick_number=player.draft_pick,
    player_id=player.player_id,
    player_name=player.name,
    position=player.position,
    college=player.background.college if player.background else "Unknown",
    event_date=Date(2025, 4, 28),
    dynasty_id="my_dynasty"
)

# Execute event
result = draft_event.simulate()
print(result.data["message"])
```

---

**End of Development Plan**
