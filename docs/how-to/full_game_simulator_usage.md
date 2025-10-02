# FullGameSimulator Usage Guide

This guide shows you how to use the cleaned, standalone FullGameSimulator for NFL game simulation.

## Quick Start

The FullGameSimulator provides a simple, standalone interface for simulating complete NFL games without any persistence overhead.

### 3-Step Usage Pattern

```python
from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs

# 1. Create simulator
simulator = FullGameSimulator(
    away_team_id=TeamIDs.DETROIT_LIONS,
    home_team_id=TeamIDs.GREEN_BAY_PACKERS
)

# 2. Run simulation
game_result = simulator.simulate_game()

# 3. Access results
final_score = simulator.get_final_score()
print(f"Final Score: {final_score}")
```

## Constructor Parameters

### Required Parameters

- **`away_team_id`** (int): Numerical team ID for the away team (1-32)
- **`home_team_id`** (int): Numerical team ID for the home team (1-32)

### Optional Parameters

- **`overtime_type`** (str): Type of overtime rules to use
  - `"regular_season"` (default): Standard regular season overtime
  - `"playoffs"`: Playoff overtime rules

### Team ID Reference

Use the `TeamIDs` constants for readable team references:

```python
from src.constants.team_ids import TeamIDs

# AFC Teams
TeamIDs.BUFFALO_BILLS          # 1
TeamIDs.MIAMI_DOLPHINS         # 2
TeamIDs.NEW_ENGLAND_PATRIOTS   # 3
# ... (all 32 teams available)

# NFC Teams
TeamIDs.DETROIT_LIONS          # 22
TeamIDs.GREEN_BAY_PACKERS      # 23
# ... etc
```

## Main Methods

### `simulate_game(date=None)`

Runs the complete NFL game simulation.

```python
# Basic simulation
game_result = simulator.simulate_game()

# With specific date
from datetime import date
game_result = simulator.simulate_game(date=date(2024, 10, 15))
```

**Returns:** `GameResult` object with complete game data

### `get_game_result()`

Access the complete game result after simulation.

```python
result = simulator.get_game_result()
if result:
    print(f"Total plays: {result.total_plays}")
    print(f"Total drives: {result.total_drives}")
    print(f"Winner: {result.winner.full_name if result.winner else 'Tie'}")
```

**Returns:** `GameResult` object or `None` if no game simulated

### `get_final_score()`

Get enhanced final score information.

```python
score_data = simulator.get_final_score()
print(f"Scores: {score_data['scores']}")           # {22: 21, 23: 14}
print(f"Team names: {score_data['team_names']}")   # {22: "Detroit Lions", 23: "Green Bay Packers"}
print(f"Winner: {score_data['winner_name']}")      # "Detroit Lions"
```

**Returns:** Dictionary with scores, team names, winner info, and metadata

### `get_team_info()`

Access detailed team information.

```python
team_info = simulator.get_team_info()
away_team = team_info['away_team']
home_team = team_info['home_team']

print(f"Away: {away_team['name']} ({away_team['abbreviation']})")
print(f"Home: {home_team['name']} ({home_team['abbreviation']})")
```

## Code Examples

### Example 1: Basic Game Simulation

```python
#!/usr/bin/env python3
from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs

def basic_game_example():
    # Create simulator
    simulator = FullGameSimulator(
        away_team_id=TeamIDs.DALLAS_COWBOYS,
        home_team_id=TeamIDs.NEW_YORK_GIANTS
    )

    # Run game
    print("🏈 Starting NFC East rivalry game...")
    game_result = simulator.simulate_game()

    # Display results
    final_score = simulator.get_final_score()

    print(f"\n🏁 FINAL SCORE:")
    for team_id, score in final_score['scores'].items():
        team_name = final_score['team_names'][team_id]
        print(f"   {team_name}: {score}")

    if final_score['winner_name']:
        print(f"🏆 Winner: {final_score['winner_name']}")
    else:
        print("🤝 Game ended in a tie")

    print(f"📊 Game Stats:")
    print(f"   Total Plays: {final_score['total_plays']}")
    print(f"   Total Drives: {final_score['total_drives']}")
    print(f"   Simulation Time: {final_score['simulation_time']:.2f}s")

if __name__ == "__main__":
    basic_game_example()
```

### Example 2: Multiple Team Combinations

```python
from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs

def division_rivalry_games():
    """Simulate games between division rivals"""

    matchups = [
        (TeamIDs.BUFFALO_BILLS, TeamIDs.NEW_ENGLAND_PATRIOTS, "AFC East"),
        (TeamIDs.PITTSBURGH_STEELERS, TeamIDs.BALTIMORE_RAVENS, "AFC North"),
        (TeamIDs.KANSAS_CITY_CHIEFS, TeamIDs.LAS_VEGAS_RAIDERS, "AFC West"),
        (TeamIDs.GREEN_BAY_PACKERS, TeamIDs.CHICAGO_BEARS, "NFC North")
    ]

    for away_id, home_id, division in matchups:
        print(f"\n🏈 {division} Rivalry Game")
        print("=" * 40)

        simulator = FullGameSimulator(away_id, home_id)
        game_result = simulator.simulate_game()

        final_score = simulator.get_final_score()
        winner = final_score['winner_name'] or "Tie"

        print(f"Winner: {winner}")
        for team_id, score in final_score['scores'].items():
            team_name = final_score['team_names'][team_id]
            print(f"  {team_name}: {score}")

if __name__ == "__main__":
    division_rivalry_games()
```

### Example 3: Playoff vs Regular Season Overtime

```python
from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs

def overtime_comparison():
    """Compare regular season vs playoff overtime rules"""

    teams = (TeamIDs.KANSAS_CITY_CHIEFS, TeamIDs.BUFFALO_BILLS)

    for overtime_type in ["regular_season", "playoffs"]:
        print(f"\n🏈 {overtime_type.replace('_', ' ').title()} Game")
        print("=" * 40)

        simulator = FullGameSimulator(
            away_team_id=teams[0],
            home_team_id=teams[1],
            overtime_type=overtime_type
        )

        game_result = simulator.simulate_game()
        final_score = simulator.get_final_score()

        print(f"Game Duration: {final_score['game_duration_minutes']} minutes")
        print(f"Total Plays: {final_score['total_plays']}")

        for team_id, score in final_score['scores'].items():
            team_name = final_score['team_names'][team_id]
            print(f"  {team_name}: {score}")

if __name__ == "__main__":
    overtime_comparison()
```

### Example 4: Accessing Team Information

```python
from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs

def team_info_example():
    """Demonstrate accessing team and roster information"""

    simulator = FullGameSimulator(
        away_team_id=TeamIDs.SAN_FRANCISCO_49ERS,
        home_team_id=TeamIDs.LOS_ANGELES_RAMS
    )

    # Get team information
    team_info = simulator.get_team_info()

    print("🏈 TEAM INFORMATION")
    print("=" * 50)

    for team_type, info in team_info.items():
        team_label = "AWAY" if team_type == "away_team" else "HOME"
        print(f"\n{team_label} TEAM: {info['name']}")
        print(f"  City: {info['city']}")
        print(f"  Conference: {info['conference']}")
        print(f"  Division: {info['division']}")
        print(f"  Colors: {', '.join(info['colors'])}")
        print(f"  Roster Size: {info['roster_size']}")

    # Get coaching staff
    away_staff = simulator.get_away_coaching_staff()
    home_staff = simulator.get_home_coaching_staff()

    print(f"\n🏈 COACHING STAFF")
    print("=" * 50)
    print(f"Away Head Coach: {away_staff['head_coach']['name']}")
    print(f"Home Head Coach: {home_staff['head_coach']['name']}")

    # Get key players
    away_qbs = simulator.get_starting_lineup(TeamIDs.SAN_FRANCISCO_49ERS, "QB")
    home_qbs = simulator.get_starting_lineup(TeamIDs.LOS_ANGELES_RAMS, "QB")

    print(f"\n🏈 STARTING QUARTERBACKS")
    print("=" * 50)
    if away_qbs:
        print(f"Away QB: {away_qbs[0].player_name} (Rating: {away_qbs[0].get_rating('overall')})")
    if home_qbs:
        print(f"Home QB: {home_qbs[0].player_name} (Rating: {home_qbs[0].get_rating('overall')})")

if __name__ == "__main__":
    team_info_example()
```

## Running Your Code

### PYTHONPATH Setup

Always run your scripts with the correct Python path:

```bash
# From project root directory
PYTHONPATH=src python your_script.py

# Or for one-liner testing
PYTHONPATH=src python -c "
from game_management.full_game_simulator import FullGameSimulator
from constants.team_ids import TeamIDs
simulator = FullGameSimulator(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
result = simulator.simulate_game()
print(f'Winner: {result.winner.full_name if result.winner else \"Tie\"}')
"
```

### Import Statements

```python
# Core simulator
from src.game_management.full_game_simulator import FullGameSimulator

# Team ID constants
from src.constants.team_ids import TeamIDs

# Optional: For date handling
from datetime import date, datetime
```

## Performance Notes

### Standalone Benefits

- **Fast startup**: No database initialization
- **Quick execution**: Typical game simulates in 0.1-0.2 seconds
- **No dependencies**: No SQLite or persistence overhead
- **Memory efficient**: Results exist only in memory
- **Reliable**: No database connection issues

### Expected Output

When you run a simulation, you'll see:

```
🏈 Full Game Simulator Initialized
   Away Team: Detroit Lions (ID: 22)
   Home Team: Green Bay Packers (ID: 23)
   Matchup: DET @ GB
   Statistics Persistence: Disabled (standalone mode)
   Coin Toss Winner: Green Bay Packers

🎮 Starting Full Game Simulation...
🏁 GAME COMPLETE!
⏱️  Simulation Time: 0.12 seconds
📊 Final Score:
   Green Bay Packers: 35
   Detroit Lions: 30
📈 Total Plays: 146
🚗 Total Drives: 25
```

## Troubleshooting

### Common Import Issues

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:** Make sure you're running with `PYTHONPATH=src`:
```bash
PYTHONPATH=src python your_script.py
```

**Problem:** `ImportError: cannot import name 'FullGameSimulator'`

**Solution:** Check your import path:
```python
# Correct
from src.game_management.full_game_simulator import FullGameSimulator

# Not this
from game_management.full_game_simulator import FullGameSimulator
```

### Team ID Validation

**Problem:** `ValueError: Could not load away team with ID: 99`

**Solution:** Use valid team IDs (1-32) via TeamIDs constants:
```python
# Good
TeamIDs.DETROIT_LIONS  # 22

# Bad
99  # Invalid team ID
```

**Problem:** `ValueError: Away and home teams must be different`

**Solution:** Use different teams:
```python
# Good
FullGameSimulator(TeamIDs.LIONS, TeamIDs.PACKERS)

# Bad
FullGameSimulator(TeamIDs.LIONS, TeamIDs.LIONS)
```

### Game State Issues

**Problem:** Trying to access results before simulation

**Solution:** Always run `simulate_game()` first:
```python
simulator = FullGameSimulator(22, 23)
# Must run simulation first
game_result = simulator.simulate_game()
# Then access results
final_score = simulator.get_final_score()
```

### Performance Issues

**Problem:** Slow simulation execution

**Solution:** The cleaned simulator should be fast. If slow:
1. Check for infinite loops in game logic
2. Verify no persistence code is running
3. Monitor for excessive logging output

## Advanced Usage

### Custom Game Scenarios

```python
# Simulate specific matchups
def simulate_playoff_game(team1_id, team2_id):
    simulator = FullGameSimulator(
        away_team_id=team1_id,
        home_team_id=team2_id,
        overtime_type="playoffs"
    )

    return simulator.simulate_game()

# Run multiple games for analysis
def simulate_season_series(team1_id, team2_id, num_games=10):
    results = []

    for game_num in range(num_games):
        # Alternate home/away
        if game_num % 2 == 0:
            away, home = team1_id, team2_id
        else:
            away, home = team2_id, team1_id

        simulator = FullGameSimulator(away, home)
        result = simulator.simulate_game()
        results.append(result)

    return results
```

### Integration with Other Systems

The FullGameSimulator is designed to integrate easily with:

- **Event-based calendar systems**: Use as simulation engine for scheduled games
- **Tournament management**: Simulate playoff brackets
- **Season simulation**: Run multiple games in sequence
- **Statistics analysis**: Process GameResult objects for analysis
- **Web interfaces**: Fast enough for real-time simulation requests

## Next Steps

- **Event Integration**: Use with the calendar system for scheduled simulations
- **Tournament Simulation**: Build playoff bracket simulation
- **Statistics Analysis**: Process multiple GameResult objects for trends
- **Custom Scenarios**: Create specific game situation testing

For more advanced usage patterns, see the existing demo scripts:
- `cleveland_browns_vs_houston_texans_demo.py` - Comprehensive demo
- `demo/` directory - Component-specific examples