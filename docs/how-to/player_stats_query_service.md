# PlayerStatsQueryService Usage Guide

## Overview

The `PlayerStatsQueryService` provides a clean, reusable API for querying player statistics from live NFL game simulations. It centralizes stats access patterns and eliminates the need for direct navigation through internal controller structures.

**Location:** `src/game_management/player_stats_query_service.py`

## Why Use PlayerStatsQueryService?

### Before (Hardcoded Access)
```python
# Direct access to internal controller structures (not recommended)
simulator = game_event._simulator
game_loop_controller = simulator._game_loop_controller
stats_aggregator = game_loop_controller.stats_aggregator
all_player_stats = stats_aggregator.player_stats.get_all_players_with_stats()

# Manual filtering
away_stats = []
for player_stat in all_player_stats:
    if player_stat.team_id == TeamIDs.DETROIT_LIONS:
        away_stats.append(player_stat)
```

### After (Using PlayerStatsQueryService)
```python
# Clean API access
from game_management.player_stats_query_service import PlayerStatsQueryService

all_player_stats = PlayerStatsQueryService.get_live_stats(simulator)
away_stats = PlayerStatsQueryService.get_stats_by_team(all_player_stats, TeamIDs.DETROIT_LIONS)
```

## Core Methods

### 1. Get Live Stats from Simulation

Extract all player statistics from a completed game simulation:

```python
from game_management.player_stats_query_service import PlayerStatsQueryService

# After running a game simulation
simulator = game_event._simulator
all_stats = PlayerStatsQueryService.get_live_stats(simulator)

print(f"Found stats for {len(all_stats)} players")
# Output: Found stats for 90 players
```

**Returns:** `List[PlayerStats]` - All players with recorded statistics

**Use Cases:**
- Box score generation
- Post-game analysis
- Statistics reporting
- Player performance tracking

---

### 2. Filter Stats by Team

Get statistics for a specific team:

```python
from constants.team_ids import TeamIDs

# Get all stats first
all_stats = PlayerStatsQueryService.get_live_stats(simulator)

# Filter by team
lions_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, TeamIDs.DETROIT_LIONS)
packers_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, TeamIDs.GREEN_BAY_PACKERS)

print(f"Lions players: {len(lions_stats)}")
print(f"Packers players: {len(packers_stats)}")
# Output: Lions players: 45
# Output: Packers players: 45
```

**Parameters:**
- `player_stats`: List of PlayerStats to filter
- `team_id`: Numerical team ID (1-32)

**Returns:** `List[PlayerStats]` - Players from specified team

**Use Cases:**
- Team-specific box scores
- Team performance analysis
- Roster participation tracking

---

### 3. Filter Stats by Position

Get statistics for players at a specific position:

```python
# Get all stats for a team
lions_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, TeamIDs.DETROIT_LIONS)

# Filter by position
qbs = PlayerStatsQueryService.get_stats_by_position(lions_stats, "QB")
rbs = PlayerStatsQueryService.get_stats_by_position(lions_stats, "RB")
wrs = PlayerStatsQueryService.get_stats_by_position(lions_stats, "WR")

print(f"Quarterbacks: {len(qbs)}")
print(f"Running Backs: {len(rbs)}")
print(f"Wide Receivers: {len(wrs)}")
```

**Parameters:**
- `player_stats`: List of PlayerStats to filter
- `position`: Position code ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB")

**Returns:** `List[PlayerStats]` - Players at specified position

**Use Cases:**
- Position group analysis
- Depth chart evaluation
- Specialized reports

---

### 4. Get Quarterback Stats

Convenience method for finding all quarterbacks (players with passing attempts):

```python
# Get quarterbacks from team stats
qbs = PlayerStatsQueryService.get_quarterback_stats(lions_stats)

for qb in qbs:
    completions = qb.passing_completions
    attempts = qb.passing_attempts
    yards = qb.passing_yards
    print(f"{qb.player_name}: {completions}/{attempts}, {yards} yards")

# Output:
# Jared Goff: 22/35, 287 yards
# Hendon Hooker: 2/3, 18 yards
```

**Returns:** `List[PlayerStats]` - Players with `passing_attempts > 0`

**Use Cases:**
- Passing statistics sections
- QB performance comparison
- Passer rating calculations

---

### 5. Get Rusher Stats

Convenience method for finding all rushers (players with rushing attempts):

```python
# Get rushers from team stats
rushers = PlayerStatsQueryService.get_rusher_stats(lions_stats)

for rusher in rushers:
    attempts = rusher.rushing_attempts
    yards = rusher.rushing_yards
    avg = yards / attempts if attempts > 0 else 0
    print(f"{rusher.player_name}: {attempts} att, {yards} yds, {avg:.1f} avg")

# Output:
# David Montgomery: 18 att, 87 yds, 4.8 avg
# Jahmyr Gibbs: 12 att, 63 yds, 5.2 avg
```

**Returns:** `List[PlayerStats]` - Players with `rushing_attempts > 0`

**Use Cases:**
- Rushing statistics sections
- Running back performance tracking
- Ground game analysis

---

### 6. Get Receiver Stats

Convenience method for finding all receivers (players with targets):

```python
# Get receivers from team stats
receivers = PlayerStatsQueryService.get_receiver_stats(lions_stats)

for receiver in receivers:
    receptions = receiver.receptions
    targets = receiver.targets
    yards = receiver.receiving_yards
    print(f"{receiver.player_name}: {receptions}/{targets} for {yards} yards")

# Output:
# Amon-Ra St. Brown: 8/11 for 102 yards
# Jameson Williams: 6/9 for 94 yards
# Sam LaPorta: 5/7 for 68 yards
```

**Returns:** `List[PlayerStats]` - Players with `targets > 0`

**Use Cases:**
- Receiving statistics sections
- Target distribution analysis
- Pass-catching performance

---

### 7. Get Players with Snaps

Get all players who participated in the game (played at least one snap):

```python
# Get all players who saw action
participants = PlayerStatsQueryService.get_players_with_snaps(all_stats)

print(f"Total players who participated: {len(participants)}")

# Show snap counts
for player in participants:
    off_snaps = player.offensive_snaps
    def_snaps = player.defensive_snaps
    print(f"{player.player_name}: {off_snaps} off, {def_snaps} def")
```

**Returns:** `List[PlayerStats]` - Players with `offensive_snaps > 0` OR `defensive_snaps > 0` OR `total_snaps > 0`

**Use Cases:**
- Complete box scores
- Participation tracking
- Snap count analysis
- Playing time reports

---

### 8. Get Top Performers

Find top performers in a specific statistical category:

```python
# Get top 5 rushers by yards
top_rushers = PlayerStatsQueryService.get_top_performers(
    all_stats,
    stat_attribute="rushing_yards",
    limit=5
)

print("Top 5 Rushers:")
for i, rusher in enumerate(top_rushers, 1):
    print(f"{i}. {rusher.player_name}: {rusher.rushing_yards} yards")

# Get top 3 passers with minimum 10 attempts
top_passers = PlayerStatsQueryService.get_top_performers(
    all_stats,
    stat_attribute="passing_yards",
    limit=3,
    minimum_threshold=10
)
```

**Parameters:**
- `player_stats`: List of PlayerStats to analyze
- `stat_attribute`: Attribute name to sort by (e.g., "passing_yards", "rushing_yards", "receptions")
- `limit`: Maximum number of players to return (default: 5)
- `minimum_threshold`: Optional minimum value for inclusion

**Returns:** `List[PlayerStats]` - Top performers sorted descending

**Use Cases:**
- Statistical leaderboards
- Game highlights
- Performance rankings
- Award tracking

---

## Complete Example: Box Score Generation

Here's a complete example showing how to generate a comprehensive box score using the service:

```python
from game_management.player_stats_query_service import PlayerStatsQueryService
from constants.team_ids import TeamIDs

# After game simulation
simulator = game_event._simulator

# Get all live stats
all_stats = PlayerStatsQueryService.get_live_stats(simulator)

# Filter by teams
lions_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, TeamIDs.DETROIT_LIONS)
packers_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, TeamIDs.GREEN_BAY_PACKERS)

# === PASSING STATISTICS ===
print("DETROIT LIONS PASSING")
print("-" * 80)
print(f"{'Player':<25} {'C/Att':<10} {'Yards':<8} {'TD':<6} {'INT':<6}")

qbs = PlayerStatsQueryService.get_quarterback_stats(lions_stats)
for qb in qbs:
    comp = qb.passing_completions
    att = qb.passing_attempts
    yards = qb.passing_yards
    tds = qb.passing_touchdowns
    ints = qb.interceptions_thrown
    print(f"{qb.player_name:<25} {comp}/{att:<8} {yards:<8} {tds:<6} {ints:<6}")

# === RUSHING STATISTICS ===
print("\nDETROIT LIONS RUSHING")
print("-" * 80)
print(f"{'Player':<25} {'Att':<8} {'Yards':<8} {'Avg':<8} {'TD':<6}")

rushers = PlayerStatsQueryService.get_rusher_stats(lions_stats)
for rusher in rushers:
    att = rusher.rushing_attempts
    yards = rusher.rushing_yards
    avg = yards / att if att > 0 else 0
    tds = rusher.rushing_touchdowns
    print(f"{rusher.player_name:<25} {att:<8} {yards:<8} {avg:<8.1f} {tds:<6}")

# === RECEIVING STATISTICS ===
print("\nDETROIT LIONS RECEIVING")
print("-" * 80)
print(f"{'Player':<25} {'Rec/Tgt':<12} {'Yards':<8} {'Avg':<8} {'TD':<6}")

receivers = PlayerStatsQueryService.get_receiver_stats(lions_stats)
for receiver in receivers:
    rec = receiver.receptions
    tgt = receiver.targets
    yards = receiver.receiving_yards
    avg = yards / rec if rec > 0 else 0
    tds = receiver.receiving_touchdowns
    print(f"{receiver.player_name:<25} {rec}/{tgt:<10} {yards:<8} {avg:<8.1f} {tds:<6}")

# === SNAP COUNTS ===
print("\nDETROIT LIONS SNAP COUNTS")
print("-" * 80)
print(f"{'Player':<25} {'Position':<10} {'Offense':<10} {'Defense':<10}")

participants = PlayerStatsQueryService.get_players_with_snaps(lions_stats)
for player in participants:
    print(f"{player.player_name:<25} {player.position:<10} {player.offensive_snaps:<10} {player.defensive_snaps:<10}")
```

---

## Integration with UI and APIs

The PlayerStatsQueryService is designed for easy integration with user interfaces and API endpoints:

### Flask API Example
```python
from flask import Flask, jsonify
from game_management.player_stats_query_service import PlayerStatsQueryService

app = Flask(__name__)

@app.route('/api/game/<game_id>/stats/team/<int:team_id>')
def get_team_stats(game_id, team_id):
    # Retrieve simulator from game storage
    simulator = get_simulator_by_game_id(game_id)

    # Get stats using service
    all_stats = PlayerStatsQueryService.get_live_stats(simulator)
    team_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, team_id)

    # Convert to JSON-serializable format
    return jsonify({
        'game_id': game_id,
        'team_id': team_id,
        'player_count': len(team_stats),
        'players': [player_to_dict(p) for p in team_stats]
    })

@app.route('/api/game/<game_id>/leaders/passing')
def get_passing_leaders(game_id):
    simulator = get_simulator_by_game_id(game_id)
    all_stats = PlayerStatsQueryService.get_live_stats(simulator)

    # Get top 5 passers
    top_passers = PlayerStatsQueryService.get_top_performers(
        all_stats,
        stat_attribute="passing_yards",
        limit=5,
        minimum_threshold=10
    )

    return jsonify({
        'category': 'passing_yards',
        'leaders': [player_to_dict(p) for p in top_passers]
    })
```

### React Component Example
```javascript
import React, { useEffect, useState } from 'react';

function TeamStatsDisplay({ gameId, teamId }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // Fetch stats from API endpoint that uses PlayerStatsQueryService
    fetch(`/api/game/${gameId}/stats/team/${teamId}`)
      .then(res => res.json())
      .then(data => setStats(data));
  }, [gameId, teamId]);

  if (!stats) return <div>Loading...</div>;

  return (
    <div>
      <h2>Team Statistics</h2>
      <p>Players: {stats.player_count}</p>
      <ul>
        {stats.players.map(player => (
          <li key={player.player_id}>{player.player_name}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

## Advanced Use Cases

### 1. Combine Multiple Filters
```python
# Get all running backs who rushed for at least 50 yards
all_stats = PlayerStatsQueryService.get_live_stats(simulator)
rbs = PlayerStatsQueryService.get_stats_by_position(all_stats, "RB")

productive_rbs = [
    rb for rb in rbs
    if rb.rushing_yards >= 50
]

print(f"RBs with 50+ yards: {len(productive_rbs)}")
```

### 2. Calculate Team Totals
```python
# Calculate team passing totals
team_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, TeamIDs.DETROIT_LIONS)
qbs = PlayerStatsQueryService.get_quarterback_stats(team_stats)

total_completions = sum(qb.passing_completions for qb in qbs)
total_attempts = sum(qb.passing_attempts for qb in qbs)
total_yards = sum(qb.passing_yards for qb in qbs)

print(f"Team Passing: {total_completions}/{total_attempts}, {total_yards} yards")
```

### 3. Performance Comparison
```python
# Compare QB performances
qbs = PlayerStatsQueryService.get_quarterback_stats(all_stats)

for qb in qbs:
    attempts = qb.passing_attempts
    if attempts > 0:
        comp_pct = (qb.passing_completions / attempts) * 100
        yards_per_att = qb.passing_yards / attempts
        print(f"{qb.player_name}: {comp_pct:.1f}% completion, {yards_per_att:.1f} YPA")
```

### 4. Game Highlights Detection
```python
# Find explosive plays (20+ yard receptions)
receivers = PlayerStatsQueryService.get_receiver_stats(all_stats)

for receiver in receivers:
    if receiver.receiving_yards >= 20 and receiver.receptions > 0:
        avg = receiver.receiving_yards / receiver.receptions
        if avg >= 20:
            print(f"🔥 {receiver.player_name}: {receiver.receptions} rec, {receiver.receiving_yards} yds (explosive!)")
```

---

## Best Practices

### 1. Always Extract Live Stats First
```python
# ✅ Good - Extract once, filter multiple times
all_stats = PlayerStatsQueryService.get_live_stats(simulator)
team1_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, team1_id)
team2_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, team2_id)

# ❌ Bad - Extracting live stats multiple times (inefficient)
team1_stats = PlayerStatsQueryService.get_stats_by_team(
    PlayerStatsQueryService.get_live_stats(simulator), team1_id
)
```

### 2. Use Type Hints for Better IDE Support
```python
from typing import List
from play_engine.simulation.stats import PlayerStats

all_stats: List[PlayerStats] = PlayerStatsQueryService.get_live_stats(simulator)
qbs: List[PlayerStats] = PlayerStatsQueryService.get_quarterback_stats(all_stats)
```

### 3. Handle Edge Cases
```python
# Check for empty results
rushers = PlayerStatsQueryService.get_rusher_stats(team_stats)
if not rushers:
    print("No rushing attempts recorded")
else:
    for rusher in rushers:
        # Process rusher stats
        pass

# Safe division
attempts = qb.passing_attempts
avg = qb.passing_yards / attempts if attempts > 0 else 0
```

### 4. Use Convenience Methods When Appropriate
```python
# ✅ Good - Use convenience method
qbs = PlayerStatsQueryService.get_quarterback_stats(team_stats)

# ❌ Unnecessary - Manual filtering when convenience method exists
qbs = [p for p in team_stats if p.passing_attempts > 0]
```

---

## Troubleshooting

### Issue: "NoneType has no attribute '_game_loop_controller'"
**Cause:** Attempting to access stats before game simulation completes

**Solution:**
```python
# Ensure game has completed
result = game_event.execute()
if result.success:
    simulator = game_event._simulator
    all_stats = PlayerStatsQueryService.get_live_stats(simulator)
```

### Issue: Empty stats list returned
**Cause:** No players recorded stats for the filter criteria

**Solution:**
```python
team_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, team_id)
if not team_stats:
    print(f"No stats found for team {team_id}")
    # Check if team_id is valid (1-32)
    # Check if game actually simulated
```

### Issue: Missing attributes on PlayerStats
**Cause:** Accessing attributes that don't exist on PlayerStats

**Solution:**
```python
# Use getattr with default value
tackles = getattr(player_stat, 'tackles', 0)
sacks = getattr(player_stat, 'sacks', 0)
```

---

## Future Enhancements (Phase 2)

The PlayerStatsQueryService is designed to support future database-backed stats retrieval:

```python
# Future Phase 2 API (not yet implemented)
class PlayerStatsQueryService:
    @staticmethod
    def get_database_stats(game_id: str, database_path: str) -> List[PlayerStats]:
        """Retrieve stats from persisted database."""
        # Implementation TBD
        pass

    @staticmethod
    def get_stats(source, game_id: Optional[str] = None) -> List[PlayerStats]:
        """Unified method - auto-detect live vs database source."""
        # Implementation TBD
        pass
```

---

## Related Components

- **PlayerStats** (`src/play_engine/simulation/stats.py`): Core stats data class
- **PlayerStatsAccumulator** (`src/play_engine/simulation/stats.py`): Stats collection during simulation
- **BoxScoreGenerator** (`src/game_management/box_score_generator.py`): Box score formatting
- **FullGameSimulator** (`src/game_management/full_game_simulator.py`): Game simulation engine

---

## Summary

The PlayerStatsQueryService provides:

✅ **Clean API** - No more navigating internal controller structures
✅ **Reusability** - Use across demos, UI, APIs, reports
✅ **Type Safety** - Strong typing with List[PlayerStats] returns
✅ **Convenience Methods** - Purpose-built methods for common queries
✅ **Performance** - Extract once, filter multiple times
✅ **Future-Proof** - Ready for Phase 2 database integration

**Start using it today** to simplify your stats retrieval code!
