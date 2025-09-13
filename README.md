# The Owners Sim

A comprehensive NFL football simulation engine that provides realistic gameplay simulation with detailed player statistics, coaching systems, and day-by-day season progression.

## Overview

The Owners Sim is a sophisticated NFL simulation system built in Python that models every aspect of professional football, from individual plays to full season management. The system features realistic play calling, penalty systems, coaching staff hierarchies, and now includes a complete NFL schedule generator with calendar-based simulation.

## Key Features

- **Realistic Play Simulation**: Complete play-by-play simulation with 6 core play types
- **Coaching Staff System**: Hierarchical coaching with Head Coach, Offensive/Defensive/Special Teams Coordinators
- **Formation-Based Play Calling**: Type-safe enum-based formation system with personnel packages
- **NFL Penalty System**: Realistic penalty rates (20-30% per play) with situational modifiers
- **Schedule Generator**: Create full NFL season schedules with all rules and constraints
- **Calendar-Based Simulation**: Day-by-day season progression with events (games, training, scouting)
- **Comprehensive Statistics**: Player and team statistics tracking with box score generation
- **Configurable System**: JSON-based configuration for teams, coaches, playbooks, and penalties

## Quick Start

### Prerequisites

- Python 3.13.5
- Virtual environment (recommended)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yangxiaofu/the-owners-sim.git
cd the-owners-sim

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install Python dependencies
pip install pytest

# Install schedule generator dependencies (optional)
pip install -r requirements_scheduling.txt
```

### Running a Full Game Simulation

```bash
# Run a complete game between two teams
python full_game_demo.py

# Run calendar-based season simulation
python calendar_manager_demo.py
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test suites
python -m pytest tests/test_scheduling/test_phase0.py  # Schedule generator tests
python -m pytest tests/test_game_loop_controller.py     # Game simulation tests
```

## Project Structure

```
the-owners-sim/
├── src/
│   ├── play_engine/        # Core play simulation engine
│   ├── game_management/    # Game orchestration and statistics
│   ├── team_management/    # Team and player management
│   ├── simulation/         # Calendar-based simulation system
│   ├── scheduling/         # NFL schedule generator
│   └── constants/          # Team IDs and constants
├── tests/                  # Comprehensive test suite
├── docs/                   # Documentation
│   ├── architecture/       # System architecture docs
│   └── plans/             # Development plans and roadmaps
├── templates/             # Schedule templates
└── CLAUDE.md             # AI assistant guide
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Comprehensive development guide
- [Architecture Overview](docs/architecture/play_engine.md) - System architecture
- [Schedule Generator](docs/plans/nfl_schedule_generator_development_roadmap.md) - Schedule generation system
- [Testing Guide](docs/TEST_GUIDE.md) - Testing approaches and patterns

## Team System

The simulation uses numerical team IDs (1-32) for all 32 NFL teams:

```python
from src.constants.team_ids import TeamIDs

# Example usage
lions_id = TeamIDs.DETROIT_LIONS  # 22
packers_id = TeamIDs.GREEN_BAY_PACKERS  # 23
```

## Simulation Features

### Play Types
- Run plays with formation matchups
- Pass plays (including play-action and screen passes)
- Field goals with accuracy modeling
- Punts with return simulation
- Kickoffs with touchback logic
- Two-point conversions

### Coaching System
- Head Coach with overall team philosophy
- Offensive Coordinator with play calling tendencies
- Defensive Coordinator with coverage schemes
- Special Teams Coordinator with situational decisions

### Schedule Generator (Phase 0 Complete)
- NFL division structure with all 32 teams
- Schedule models for games, weeks, and seasons
- CalendarManager integration for day-by-day simulation
- Configuration system for constraints and preferences
- Date utilities for NFL season calculations

## Development Status

### Completed
- ✅ Core play engine with match/case routing
- ✅ Comprehensive penalty system
- ✅ Coaching staff hierarchy
- ✅ Formation-based play calling
- ✅ Game state management
- ✅ Statistics aggregation
- ✅ Schedule generator foundation (Phase 0)
- ✅ Calendar-based simulation system

### In Progress
- 🔄 Schedule generator implementation (Phase 1-11)
- 🔄 Enhanced player attributes
- 🔄 Injury system

### Planned
- 📋 Draft simulation
- 📋 Contract negotiations
- 📋 Season-long franchise mode
- 📋 Web interface

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Use numerical team IDs (1-32) instead of team names
2. Follow existing code patterns and architecture
3. Add tests for new features
4. Update documentation when adding new systems
5. Use type hints for better code clarity

## Testing

The project includes comprehensive testing:

```bash
# Unit tests
python -m pytest tests/test_scheduling/

# Integration tests
python -m pytest tests/test_game_loop_controller.py

# Performance tests
python -m pytest tests/test_phase_4_comprehensive.py

# Interactive validation
python tests/simple_penalty_validation.py
```

## Recent Updates

- **Schedule Generator**: Added complete NFL schedule generation system foundation
- **Calendar Integration**: Day-by-day simulation with multiple event types
- **Enhanced Results**: Polymorphic result processing for different event types
- **Documentation**: Comprehensive documentation for all systems

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- NFL for the inspiration and rule framework
- Python community for excellent libraries
- Contributors and testers

## Contact

For questions, suggestions, or bug reports, please open an issue on GitHub.

---

**Note**: This simulation is for entertainment and educational purposes. All team names and references are property of the National Football League.