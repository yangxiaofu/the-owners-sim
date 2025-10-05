# Player Generator Demo

Interactive demonstration of the NFL player generation system implemented in Sprints 1-2.

## Overview

This demo showcases the complete player generation pipeline:
- **Statistical Distributions**: Normal and beta distributions for realistic attribute generation
- **Attribute Correlations**: Size/speed, strength/size relationships
- **Position-Specific Weights**: Different overall calculations per position
- **Draft Round Ranges**: Round 1 (75-95) through Round 7 (55-72)
- **Complete Draft Classes**: Full 7-round, 224-player draft class generation
- **Generation Contexts**: NFL Draft, UDFA, International players

## Quick Start

```bash
# Run the interactive demo
PYTHONPATH=src python demo/player_generator_demo/player_generator_demo.py
```

## Demo Features

### 1. Single Player Generation
Generates an individual draft prospect with complete attributes and metadata.

**Example Output:**
```
┌─ Michael Johnson ────────────────────────────────────────────────────────────┐
│ Position: QB         Age: 22  Overall: 85                                    │
│ Archetype: test_qb                                                           │
│ Draft: Round 1, Pick 5 (2025)                                                │
│                                                                               │
│ KEY RATINGS:                                                                 │
│   Accuracy                    92                                             │
│   Awareness                   88                                             │
│   Arm Strength                85                                             │
│   Release                     84                                             │
│   Speed                       72                                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2. Position Comparison
Shows how different positions (QB, RB, WR, EDGE) have different attribute focuses.

### 3. Draft Round Impact
Demonstrates how draft round affects overall rating ranges:
- **Round 1**: 75-95 (Elite talent)
- **Round 3**: 68-85 (Quality starters)
- **Round 5**: 62-78 (Backups)
- **Round 7**: 55-72 (Projects)

### 4. Complete Draft Class
Generates a full 7-round, 224-player draft class with:
- Position distribution statistics
- Overall rating distribution
- Elite prospect identification
- Round-by-round averages

**Example Output:**
```
TOP 10 PICKS:
────────────────────────────────────────────────────────────────────────────────
 1. Chris Williams             EDGE   Overall: 91  (test_edge)
 2. Marcus Davis               QB     Overall: 88  (test_qb)
 3. Jordan Martinez            OT     Overall: 87  (test_ot)
...

DRAFT CLASS STATISTICS
────────────────────────────────────────────────────────────────────────────────
Overall Ratings:
  Average: 69.5
  Range: 56 - 92
  Elite players (85+): 12

Position Distribution:
  CB      18  █████████
  EDGE    15  ███████
  QB      14  ███████
  RB      16  ████████
  ...
```

### 5. Name Generator
Demonstrates the realistic name generation system with unique player names.

### 6. Attribute Calculation
Shows position-weighted overall calculation examples for QB and RB positions.

### 7. Generation Contexts
Demonstrates different player generation contexts:
- **NFL Draft**: Full draft pick range (40-99 overall)
- **UDFA**: Capped at 68 overall ceiling
- **International**: Custom ranges for CFL, XFL players

## Interactive Menu

The demo provides an interactive menu for exploring different features:

```
1. Generate Single Player
2. Compare Positions
3. Draft Round Ranges
4. Complete Draft Class (224 players)
5. Name Generator
6. Attribute Calculation
7. Generation Contexts
8. Run All Demos
9. Exit
```

## Technical Details

### Components Demonstrated

**Sprint 1 - Core Infrastructure:**
- `AttributeDistribution`: Normal and beta distributions
- `AttributeCorrelation`: Correlated attribute generation
- `PlayerArchetype`: Archetype-based generation
- `GenerationConfig`: Context and round-based configuration
- `GeneratedPlayer`: Complete player data model
- `ArchetypeRegistry`: Archetype management

**Sprint 2 - Basic Generation:**
- `AttributeGenerator`: Position-specific attribute generation
- `NameGenerator`: Realistic name pools
- `PlayerGenerator`: Core generation engine
- `DraftClassGenerator`: Complete draft class generation

### Key Features Showcased

1. **Statistical Realism**: Attributes follow normal distributions within archetype ranges
2. **Position Specificity**: Each position has unique attribute weights for overall calculation
3. **Round-Based Ranges**: Draft round determines player quality ranges
4. **Attribute Correlation**: Size negatively correlates with speed (-0.6 coefficient)
5. **Complete Integration**: All components work together seamlessly

## Expected Output

Running the complete demo (option 8) will:
1. Generate a first-round QB prospect
2. Show position-specific attribute differences
3. Demonstrate round-based overall ranges
4. Generate a complete 224-player draft class
5. Show 10 unique player names
6. Demonstrate overall calculation formulas
7. Show different generation contexts

Total runtime: ~2-3 seconds for all demos including full draft class generation.

## System Requirements

- Python 3.13+
- NumPy (for beta distribution)
- No database or external dependencies required
- All generation happens in-memory

## Next Steps

After running this demo, explore:
- **Sprint 3**: Archetype JSON configuration files
- **Sprint 4**: Complete archetype library (30+ archetypes)
- **Sprint 5**: Advanced draft class features (talent variation, position scarcity)
- **Sprint 6**: Scouting system with error and confidence levels

## Troubleshooting

**Issue**: Import errors
**Solution**: Ensure you run with `PYTHONPATH=src` prefix

**Issue**: Missing numpy
**Solution**: Install with `pip install numpy`

**Issue**: No archetypes available
**Solution**: Demo uses inline test archetypes, no JSON files needed for basic functionality

## Architecture

```
demo/player_generator_demo/
├── player_generator_demo.py    # Main interactive demo
└── README.md                   # This file

Uses:
src/player_generation/
├── core/                       # Statistical distributions, correlations
├── archetypes/                 # Archetype system
├── generators/                 # Player and draft class generators
└── models/                     # GeneratedPlayer data model
```

## Performance

- Single player generation: <1ms
- Complete draft class (224 players): ~200-300ms
- Name generation (100 unique): <10ms
- Attribute calculation: <1µs per player

## Developer Notes

This demo is designed to be:
- **Self-contained**: No external data files required
- **Educational**: Clear output showing how each component works
- **Interactive**: Menu-driven for easy exploration
- **Comprehensive**: Covers all Sprint 1-2 functionality

Perfect for:
- Understanding the generation system architecture
- Testing changes to generation logic
- Demonstrating system capabilities
- Validating statistical distributions