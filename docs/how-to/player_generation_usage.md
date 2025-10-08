# Player Generation System - Usage Guide

**Last Updated**: October 2025
**Status**: Sprint 1-2 Complete (Core Infrastructure + Basic Generation)
**Version**: 1.0.0

## Overview

The player generation system provides a flexible, archetype-based framework for creating realistic NFL player prospects. This guide covers all aspects of using the system in your code.

## Quick Start

### Basic Player Generation

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.core.generation_context import GenerationConfig, GenerationContext

# Create a player generator
generator = PlayerGenerator()

# Configure generation context
config = GenerationConfig(
    context=GenerationContext.NFL_DRAFT,
    position="QB",
    draft_round=1,
    draft_pick=5,
    draft_year=2025
)

# Generate the player
player = generator.generate_player(config)

print(f"{player.name} - {player.position} - Overall: {player.true_overall}")
print(f"Player ID: {player.player_id}")
print(f"Top Ratings: {sorted(player.true_ratings.items(), key=lambda x: x[1], reverse=True)[:5]}")
```

### Complete Draft Class Generation

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.generators.draft_class_generator import DraftClassGenerator

# Create generators
player_gen = PlayerGenerator()
draft_gen = DraftClassGenerator(player_gen)

# Generate complete 7-round draft class (224 players)
draft_class = draft_gen.generate_draft_class(year=2025)

print(f"Generated {len(draft_class)} players")
for i, player in enumerate(draft_class[:10], 1):
    print(f"{i:2d}. {player.name:<25} {player.position:<6} Overall: {player.true_overall:2d}")
```

## Core Components

### 1. PlayerGenerator

The main entry point for player generation.

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.archetypes.archetype_registry import ArchetypeRegistry

# Default usage (creates internal registry)
generator = PlayerGenerator()

# With custom archetype registry
custom_registry = ArchetypeRegistry()
# ... add custom archetypes to registry ...
generator = PlayerGenerator(registry=custom_registry)
```

**Key Methods**:

```python
def generate_player(
    config: GenerationConfig,
    archetype: Optional[PlayerArchetype] = None
) -> GeneratedPlayer:
    """
    Generate a single player.

    Args:
        config: Generation configuration (context, position, draft info)
        archetype: Optional specific archetype (selects randomly if not provided)

    Returns:
        GeneratedPlayer with all attributes and metadata
    """
```

### 2. GenerationConfig

Configures the generation context and constraints.

```python
from player_generation.core.generation_context import GenerationConfig, GenerationContext

# NFL Draft prospect
config = GenerationConfig(
    context=GenerationContext.NFL_DRAFT,
    position="WR",              # Position to generate
    draft_round=2,              # Draft round (1-7)
    draft_pick=45,              # Overall pick number
    draft_year=2025,            # Draft year
    age=22                      # Optional: override default age
)

# Undrafted Free Agent
config = GenerationConfig(
    context=GenerationContext.UDFA,
    position="RB"
    # UDFA capped at 68 overall ceiling
)

# Custom generation
config = GenerationConfig(
    context=GenerationContext.CUSTOM,
    position="QB",
    archetype_id="elite_pocket_passer",  # Specific archetype
    age=25
)
```

**Generation Contexts**:

| Context | Description | Overall Range | Use Case |
|---------|-------------|---------------|----------|
| `NFL_DRAFT` | Draft prospects | Round-based (40-99) | Main draft generation |
| `UDFA` | Undrafted free agents | 50-68 ceiling | Post-draft pool |
| `INTERNATIONAL_CFL` | CFL prospects | 55-75 | International players |
| `INTERNATIONAL_XFL` | XFL prospects | 50-70 | Alternative leagues |
| `CUSTOM` | Custom generation | User-defined | Special cases |

**Draft Round Overall Ranges**:

```python
# Round-based overall ranges (from GenerationConfig)
Round 1: 75-95  # Elite talent
Round 2: 70-88  # High-quality starters
Round 3: 68-85  # Quality starters
Round 4: 66-82  # Starter/backup tier
Round 5: 62-78  # Backup quality
Round 6: 58-74  # Developmental
Round 7: 55-72  # Long shots
```

### 3. GeneratedPlayer

The complete player data model.

```python
@dataclass
class GeneratedPlayer:
    player_id: str                          # Unique identifier (e.g., "DRAFT_2025_005")
    name: str                               # Generated name
    position: str                           # Position (QB, RB, WR, etc.)
    age: int                                # Player age
    true_ratings: Dict[str, int]            # Actual attribute ratings
    scouted_ratings: Dict[str, int]         # Scouted ratings (with error)
    true_overall: int                       # Actual overall rating
    scouted_overall: int                    # Scouted overall rating
    archetype_id: str                       # Source archetype
    generation_context: str                 # Generation context
    draft_round: Optional[int] = None       # Draft round (if applicable)
    draft_pick: Optional[int] = None        # Draft pick (if applicable)
```

**Key Methods**:

```python
# Convert to player dictionary (for database storage)
player_dict = player.to_player_dict()
# Returns: {"name": "...", "primary_position": "...", "ratings": {...}}

# Convert to JSON
json_str = player.to_json()

# Create from JSON
player = GeneratedPlayer.from_json(json_str)
```

### 4. AttributeGenerator

Generates player attributes with position-specific weighting.

```python
from player_generation.generators.attribute_generator import AttributeGenerator
from player_generation.archetypes.base_archetype import PlayerArchetype, AttributeRange, Position

# Create archetype
archetype = PlayerArchetype(
    archetype_id="balanced_qb",
    position=Position.QB,
    name="Balanced QB",
    description="Well-rounded quarterback",
    physical_attributes={
        "speed": AttributeRange(min=65, max=80, mean=72, std_dev=5),
        "strength": AttributeRange(min=70, max=85, mean=77, std_dev=5),
        "agility": AttributeRange(min=70, max=85, mean=77, std_dev=5)
    },
    mental_attributes={
        "awareness": AttributeRange(min=75, max=95, mean=85, std_dev=5)
    },
    position_attributes={
        "accuracy": AttributeRange(min=80, max=99, mean=90, std_dev=5),
        "arm_strength": AttributeRange(min=75, max=92, mean=83, std_dev=6)
    },
    overall_range=AttributeRange(min=70, max=95, mean=82, std_dev=8),
    frequency=1.0,
    peak_age_range=(28, 32),
    development_curve="normal"
)

# Generate attributes
attributes = AttributeGenerator.generate_attributes(archetype)
# Returns: {"speed": 73, "strength": 79, "agility": 75, "awareness": 87, "accuracy": 92, "arm_strength": 85}

# Calculate overall rating
overall = AttributeGenerator.calculate_overall(attributes, "QB")
# Returns: 84 (weighted by QB-specific formula)
```

**Position-Specific Overall Weights**:

```python
# QB weights (from AttributeGenerator)
"accuracy": 0.25,
"arm_strength": 0.20,
"awareness": 0.20,
"speed": 0.10,
"agility": 0.08,
"strength": 0.05,
# ... other attributes ...

# RB weights
"speed": 0.25,
"agility": 0.20,
"strength": 0.15,
"carrying": 0.15,
"elusiveness": 0.12,
"vision": 0.08,
# ... other attributes ...

# WR weights
"speed": 0.25,
"catching": 0.22,
"route_running": 0.18,
"agility": 0.12,
"awareness": 0.10,
# ... other attributes ...
```

### 5. NameGenerator

Generates realistic player names.

```python
from player_generation.generators.name_generator import NameGenerator

# Generate single name
name = NameGenerator.generate_name()
# Returns: "Michael Johnson" (random from name pools)

# Generate multiple unique names
names = NameGenerator.generate_unique_names(count=10)
# Returns: ["Michael Johnson", "Chris Williams", ...] (all unique)
```

**Name Pools**:
- 56 first names (diverse, NFL-realistic)
- 60 last names (diverse, NFL-realistic)
- Total combinations: 3,360 unique names

### 6. DraftClassGenerator

Generates complete NFL draft classes with realistic position distribution.

```python
from player_generation.generators.draft_class_generator import DraftClassGenerator

# Position distribution by round
POSITION_DISTRIBUTION = {
    1: {  # Round 1: Premium positions
        "QB": 0.15, "EDGE": 0.20, "OT": 0.20, "WR": 0.15,
        "CB": 0.15, "DT": 0.10, "S": 0.05
    },
    2: {  # Round 2
        "QB": 0.10, "RB": 0.10, "WR": 0.15, "OT": 0.15,
        "EDGE": 0.15, "CB": 0.15, "S": 0.10, "LB": 0.10
    },
    # ... rounds 3-7 with increasing position diversity
}

# Generate draft class
generator = PlayerGenerator()
class_gen = DraftClassGenerator(generator)
draft_class = class_gen.generate_draft_class(year=2025)

# Total: 224 players (7 rounds × 32 picks)
# Position distribution matches NFL draft trends
# Overall ratings decline by round
```

## Common Use Cases

### 1. Dynasty Mode - Annual Draft

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.generators.draft_class_generator import DraftClassGenerator

def generate_annual_draft(year: int) -> List[GeneratedPlayer]:
    """Generate draft class for dynasty mode."""
    generator = PlayerGenerator()
    class_gen = DraftClassGenerator(generator)

    draft_class = class_gen.generate_draft_class(year=year)

    # Filter by team needs, scouting reports, etc.
    return draft_class

# Usage
draft_2025 = generate_annual_draft(2025)
draft_2026 = generate_annual_draft(2026)
```

### 2. Team Builder - Fill Roster Gaps

```python
def fill_roster_position(position: str, count: int) -> List[GeneratedPlayer]:
    """Generate players for specific position needs."""
    generator = PlayerGenerator()
    players = []

    for i in range(count):
        config = GenerationConfig(
            context=GenerationContext.UDFA,
            position=position
        )
        player = generator.generate_player(config)
        players.append(player)

    return players

# Usage
backup_qbs = fill_roster_position("QB", 2)
wide_receivers = fill_roster_position("WR", 3)
```

### 3. Mock Draft Simulator

```python
def simulate_mock_draft(team_needs: Dict[int, str]) -> Dict[int, GeneratedPlayer]:
    """
    Simulate mock draft based on team needs.

    Args:
        team_needs: {pick_number: position}

    Returns:
        {pick_number: GeneratedPlayer}
    """
    generator = PlayerGenerator()
    picks = {}

    for pick_num, position in sorted(team_needs.items()):
        round_num = (pick_num - 1) // 32 + 1

        config = GenerationConfig(
            context=GenerationContext.NFL_DRAFT,
            position=position,
            draft_round=round_num,
            draft_pick=pick_num,
            draft_year=2025
        )

        player = generator.generate_player(config)
        picks[pick_num] = player

    return picks

# Usage
team_needs = {
    1: "QB",
    5: "EDGE",
    10: "OT",
    # ... etc
}
mock_results = simulate_mock_draft(team_needs)
```

### 4. Scouting System Integration

```python
def generate_draft_board(
    top_n: int = 100,
    include_scouting_error: bool = True
) -> List[GeneratedPlayer]:
    """Generate top prospects for scouting board."""
    generator = PlayerGenerator()
    prospects = []

    # Generate top rounds only
    for round_num in range(1, 4):  # Rounds 1-3
        for pick in range(1, 33):
            overall_pick = (round_num - 1) * 32 + pick

            config = GenerationConfig(
                context=GenerationContext.NFL_DRAFT,
                draft_round=round_num,
                draft_pick=overall_pick,
                draft_year=2025
            )

            player = generator.generate_player(config)
            prospects.append(player)

    # Sort by scouted overall (with error) if enabled
    if include_scouting_error:
        prospects.sort(key=lambda p: p.scouted_overall, reverse=True)
    else:
        prospects.sort(key=lambda p: p.true_overall, reverse=True)

    return prospects[:top_n]

# Usage
draft_board = generate_draft_board(top_n=50, include_scouting_error=True)
```

### 5. Custom Archetype Generation

```python
from player_generation.archetypes.base_archetype import PlayerArchetype, Position, AttributeRange
from player_generation.archetypes.archetype_registry import ArchetypeRegistry

def create_custom_archetype_registry():
    """Create registry with custom archetypes."""
    registry = ArchetypeRegistry()

    # Create elite QB archetype
    elite_qb = PlayerArchetype(
        archetype_id="elite_qb_prospect",
        position=Position.QB,
        name="Elite QB Prospect",
        description="Top-tier QB with franchise potential",
        physical_attributes={
            "speed": AttributeRange(min=70, max=85, mean=77, std_dev=4),
            "strength": AttributeRange(min=75, max=90, mean=82, std_dev=4),
            "agility": AttributeRange(min=75, max=90, mean=82, std_dev=4)
        },
        mental_attributes={
            "awareness": AttributeRange(min=85, max=99, mean=92, std_dev=4)
        },
        position_attributes={
            "accuracy": AttributeRange(min=88, max=99, mean=94, std_dev=3),
            "arm_strength": AttributeRange(min=85, max=99, mean=92, std_dev=4)
        },
        overall_range=AttributeRange(min=85, max=99, mean=92, std_dev=4),
        frequency=0.05,  # 5% of QBs are elite
        peak_age_range=(28, 32),
        development_curve="normal"
    )

    registry.archetypes[elite_qb.archetype_id] = elite_qb
    return registry

# Usage
custom_registry = create_custom_archetype_registry()
generator = PlayerGenerator(registry=custom_registry)

config = GenerationConfig(
    context=GenerationContext.NFL_DRAFT,
    position="QB",
    archetype_id="elite_qb_prospect",  # Use specific archetype
    draft_round=1,
    draft_pick=1,
    draft_year=2025
)

elite_prospect = generator.generate_player(config)
```

### 6. Database Integration

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.core.generation_context import GenerationConfig, GenerationContext

def save_generated_player_to_db(player: GeneratedPlayer, db_connection):
    """Save generated player to database."""
    # Convert to dictionary format
    player_data = player.to_player_dict()

    # Add metadata
    player_data.update({
        "player_id": player.player_id,
        "age": player.age,
        "archetype_id": player.archetype_id,
        "draft_round": player.draft_round,
        "draft_pick": player.draft_pick,
        "true_overall": player.true_overall,
        "scouted_overall": player.scouted_overall
    })

    # Insert into database
    cursor = db_connection.cursor()
    cursor.execute("""
        INSERT INTO generated_players
        (player_id, name, position, age, true_ratings, scouted_ratings,
         true_overall, scouted_overall, archetype_id, draft_round, draft_pick)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        player.player_id,
        player.name,
        player.position,
        player.age,
        json.dumps(player.true_ratings),
        json.dumps(player.scouted_ratings),
        player.true_overall,
        player.scouted_overall,
        player.archetype_id,
        player.draft_round,
        player.draft_pick
    ))
    db_connection.commit()

# Usage
generator = PlayerGenerator()
config = GenerationConfig(
    context=GenerationContext.NFL_DRAFT,
    position="QB",
    draft_round=1,
    draft_pick=1,
    draft_year=2025
)
player = generator.generate_player(config)
save_generated_player_to_db(player, db_connection)
```

## Advanced Features

### Statistical Distributions

The system uses multiple distribution types for realistic attribute generation:

```python
from player_generation.core.distributions import AttributeDistribution

# Normal distribution (most common)
speed = AttributeDistribution.normal(
    mean=85.0,
    std_dev=5.0,
    min_val=70.0,
    max_val=99.0
)

# Beta distribution (for bounded attributes)
awareness = AttributeDistribution.beta(
    alpha=5.0,
    beta=2.0,
    min_val=60.0,
    max_val=99.0
)

# Bounded distribution (hard limits)
strength = AttributeDistribution.bounded(
    mean=80.0,
    std_dev=6.0,
    min_val=50.0,
    max_val=99.0
)
```

### Attribute Correlations

The system maintains realistic attribute relationships:

```python
from player_generation.core.correlations import AttributeCorrelation

# Defined correlations
CORRELATIONS = {
    ("size", "speed"): -0.6,        # Larger players are slower
    ("strength", "size"): 0.7,      # Larger players are stronger
    ("awareness", "experience"): 0.8,  # Experience improves awareness
    ("acceleration", "speed"): 0.9,    # Speed and acceleration linked
    ("agility", "size"): -0.5,      # Larger players less agile
}

# Correlations are automatically applied during attribute generation
```

### Player ID Formats

```python
# NFL Draft
"DRAFT_{year}_{pick:03d}"
# Example: "DRAFT_2025_005" (5th overall pick, 2025)

# UDFA
"UDFA_{random_hex}"
# Example: "UDFA_a3f9c2d1"

# Custom
"GEN_{random_hex}"
# Example: "GEN_b7e4a9f3"
```

## Performance Considerations

### Generation Speed

```python
# Single player: <1ms
# 10 players: ~5-10ms
# Complete draft class (224 players): ~200-300ms
# 1000 players: ~1-2 seconds
```

### Memory Usage

```python
# Single GeneratedPlayer: ~2-3KB
# Draft class (224 players): ~500KB
# 10,000 players: ~20-30MB
```

### Optimization Tips

```python
# 1. Reuse generator instances
generator = PlayerGenerator()  # Create once
for i in range(1000):
    player = generator.generate_player(config)  # Reuse

# 2. Batch generation for large sets
def batch_generate_players(count: int, batch_size: int = 100):
    """Generate players in batches for better memory management."""
    generator = PlayerGenerator()
    all_players = []

    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        batch = []

        for i in range(batch_start, batch_end):
            config = GenerationConfig(...)
            player = generator.generate_player(config)
            batch.append(player)

        # Process batch (save to DB, etc.)
        all_players.extend(batch)

    return all_players

# 3. Use specific archetypes when possible (faster than random selection)
config = GenerationConfig(
    archetype_id="balanced_qb",  # Faster than position-based random selection
    ...
)
```

## Error Handling

```python
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.core.generation_context import GenerationConfig, GenerationContext

try:
    generator = PlayerGenerator()
    config = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        position="QB",
        draft_round=1,
        draft_pick=5,
        draft_year=2025
    )
    player = generator.generate_player(config)

except ValueError as e:
    # Raised when:
    # - Archetype cannot be determined
    # - Invalid position specified
    # - Invalid draft round/pick combination
    print(f"Generation error: {e}")

except KeyError as e:
    # Raised when:
    # - Archetype ID not found in registry
    # - Invalid attribute reference
    print(f"Configuration error: {e}")
```

## Testing

```python
# Run player generation tests
PYTHONPATH=src python -m pytest tests/player_generation/ -v

# Run specific sprint tests
PYTHONPATH=src python -m pytest tests/player_generation/test_sprint1.py -v
PYTHONPATH=src python -m pytest tests/player_generation/test_sprint2.py -v

# Run demo
PYTHONPATH=src python demo/player_generator_demo/player_generator_demo.py
```

## Future Enhancements (Upcoming Sprints)

### Sprint 3: Archetype Configuration (Planned)
- JSON-based archetype definitions
- 30+ position-specific archetypes
- Designer-friendly archetype editor

### Sprint 4: Advanced Generation (Planned)
- Talent year variation (strong/weak draft classes)
- Position scarcity modeling
- Multi-year draft projections

### Sprint 5: Scouting System (Planned)
- Scouting reports with confidence levels
- Scout skill levels affect accuracy
- Hidden traits and bust/boom potential

### Sprint 6: Development System (Planned)
- Player progression curves
- Training effects on attributes
- Injury history and durability

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'player_generation'`
```bash
# Solution: Always use PYTHONPATH=src
PYTHONPATH=src python your_script.py
```

**Issue**: `ValueError: Could not determine archetype for generation`
```python
# Solution: Ensure archetype exists or specify archetype_id
config = GenerationConfig(
    context=GenerationContext.NFL_DRAFT,
    position="QB",  # Must have QB archetypes in registry
    draft_round=1,
    draft_pick=1
)
```

**Issue**: Generated overall doesn't match expected range
```python
# Cause: Overall calculation uses position-specific weights
# Solution: Check AttributeGenerator.calculate_overall() weights for position

# QB example: Accuracy (25%), Arm Strength (20%), Awareness (20%) are heavily weighted
# RB example: Speed (25%), Agility (20%), Strength (15%) are heavily weighted
```

## Additional Resources

- **Demo**: `demo/player_generator_demo/` - Interactive demonstrations
- **Tests**: `tests/player_generation/` - Comprehensive test suite
- **Plan**: `docs/plans/player_generator_plan.md` - Development roadmap
- **Spec**: `docs/specifications/player_generator_system.md` - Technical specification

## Support

For questions or issues:
1. Check the demo: `PYTHONPATH=src python demo/player_generator_demo/player_generator_demo.py`
2. Review tests: `tests/player_generation/test_sprint1.py` and `test_sprint2.py`
3. Consult the plan: `docs/plans/player_generator_plan.md`
