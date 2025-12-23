# TeamContextBuilder Usage Guide

## Overview

`TeamContextBuilder` is a service that builds rich team context for social media posts and other systems. It aggregates:

- **Team Record**: Wins, losses, ties, win percentage
- **Rankings**: Division rank (1-4), conference rank (1-16)
- **Playoff Position**: CLINCHED, IN_HUNT, ELIMINATED, LEADER, or UNKNOWN
- **Season Phase**: EARLY (weeks 1-6), MID (7-12), LATE (13-18), or PLAYOFFS
- **Recent Activity**: Trades, signings, cuts from the last 2 weeks
- **Streaks**: Current win/loss streak with count

## Quick Start

```python
from game_cycle.database.connection import GameCycleDatabase
from game_cycle.services.team_context_builder import TeamContextBuilder

# Initialize
db = GameCycleDatabase("data/database/game_cycle/game_cycle.db")
builder = TeamContextBuilder(db)

# Build context
context = builder.build_context(
    dynasty_id="your_dynasty_id",
    season=2025,
    team_id=22,  # Detroit Lions
    week=10
)

# Access context data
print(f"{context.team_name} ({context.get_record_string()})")
print(f"Division Rank: {context.division_rank}")
print(f"Playoff Position: {context.playoff_position.value}")
print(f"Current Streak: {context.get_streak_string()}")
```

## TeamContext Fields

### Basic Info
```python
context.team_id          # Team ID (1-32)
context.team_name        # Team name (e.g., "Detroit Lions")
context.season           # Season year
context.week             # Current week (1-18) or None for playoffs/offseason
```

### Record
```python
context.wins             # Total wins
context.losses           # Total losses
context.ties             # Total ties
context.win_pct          # Win percentage (0.0 - 1.0)
context.get_record_string()  # Returns "10-4-0"
context.is_winning_record()  # Returns True if win% > 0.500
```

### Rankings
```python
context.division_rank    # Rank in division (1-4)
context.conference_rank  # Rank in conference (1-16)
```

### Playoff Position
```python
context.playoff_position  # PlayoffPosition enum
context.is_playoff_team() # True if CLINCHED or LEADER

# Possible values:
# - PlayoffPosition.CLINCHED: Playoff spot secured
# - PlayoffPosition.LEADER: Leading division
# - PlayoffPosition.IN_HUNT: In playoff contention
# - PlayoffPosition.ELIMINATED: Mathematically eliminated
# - PlayoffPosition.UNKNOWN: Too early to determine
```

### Season Phase
```python
context.season_phase  # SeasonPhase enum

# Possible values:
# - SeasonPhase.EARLY: Weeks 1-6
# - SeasonPhase.MID: Weeks 7-12
# - SeasonPhase.LATE: Weeks 13-18
# - SeasonPhase.PLAYOFFS: Postseason
```

### Recent Activity
```python
context.recent_trades    # List of trades (last 2 weeks)
context.recent_signings  # List of FA signings (last 2 weeks)
context.recent_cuts      # List of roster cuts (last 2 weeks)
context.has_recent_activity()  # True if any activity

# Transaction format:
# {
#     'id': 123,
#     'type': 'TRADE',
#     'player_id': 12345,
#     'player_name': 'John Smith',
#     'position': 'WR',
#     'from_team_id': 22,
#     'to_team_id': 23,
#     'date': '2025-10-15',
#     'details': {...}
# }
```

### Streaks
```python
context.current_streak   # Positive integer (number of games)
context.streak_type      # 'W' or 'L'
context.get_streak_string()  # Returns "W3" or "L2" or ""
```

## Usage Examples

### Social Media Post Generator

```python
def generate_game_recap_post(dynasty_id: str, season: int, team_id: int, week: int):
    """Generate social media post with team context."""
    builder = TeamContextBuilder(db)
    context = builder.build_context(dynasty_id, season, team_id, week)

    # Use context in post generation
    if context.is_playoff_team():
        tone = "playoff_contender"
    elif context.is_winning_record():
        tone = "positive"
    else:
        tone = "struggling"

    # Include streak in post
    if context.current_streak >= 3:
        mention_streak = True

    # Check for recent trades
    if context.recent_trades:
        mention_roster_moves = True

    # Adjust messaging based on season phase
    if context.season_phase == SeasonPhase.LATE:
        emphasize_playoff_implications = True
```

### Playoff Picture Analysis

```python
def analyze_playoff_picture(dynasty_id: str, season: int):
    """Analyze playoff picture for all teams."""
    builder = TeamContextBuilder(db)

    for team_id in range(1, 33):
        context = builder.build_context(dynasty_id, season, team_id, week=14)

        if context.playoff_position == PlayoffPosition.CLINCHED:
            print(f"✓ {context.team_name} - CLINCHED")
        elif context.playoff_position == PlayoffPosition.LEADER:
            print(f"👑 {context.team_name} - DIVISION LEADER")
        elif context.playoff_position == PlayoffPosition.IN_HUNT:
            print(f"🔥 {context.team_name} - IN THE HUNT")
```

### Team Performance Summary

```python
def get_team_summary(dynasty_id: str, season: int, team_id: int, week: int):
    """Get comprehensive team summary."""
    builder = TeamContextBuilder(db)
    context = builder.build_context(dynasty_id, season, team_id, week)

    summary = {
        'team': context.team_name,
        'record': context.get_record_string(),
        'win_percentage': context.win_pct,
        'division_standing': f"{context.division_rank}/4",
        'conference_standing': f"{context.conference_rank}/16",
        'playoff_status': context.playoff_position.value,
        'season_phase': context.season_phase.value,
        'streak': context.get_streak_string(),
        'recent_moves': len(context.recent_trades + context.recent_signings + context.recent_cuts)
    }

    return summary
```

### Conditional Post Content

```python
def customize_post_content(context: TeamContext) -> dict:
    """Customize post content based on context."""
    content = {}

    # Season phase adjustments
    if context.season_phase == SeasonPhase.EARLY:
        content['focus'] = 'establishing_identity'
    elif context.season_phase == SeasonPhase.MID:
        content['focus'] = 'playoff_positioning'
    else:  # LATE
        content['focus'] = 'playoff_push'

    # Playoff position messaging
    if context.playoff_position == PlayoffPosition.CLINCHED:
        content['tone'] = 'celebratory'
    elif context.playoff_position == PlayoffPosition.ELIMINATED:
        content['tone'] = 'looking_ahead'

    # Hot/cold team detection
    if context.current_streak >= 4:
        if context.streak_type == 'W':
            content['narrative'] = 'red_hot'
        else:
            content['narrative'] = 'struggling'

    # Recent activity
    if context.recent_trades:
        content['mention_trades'] = True

    return content
```

## Integration with Social Media System

```python
from game_cycle.services.team_context_builder import TeamContextBuilder
from game_cycle.services.social_post_generator import SocialPostGenerator

def generate_weekly_posts(dynasty_id: str, season: int, week: int):
    """Generate social media posts for all teams."""
    builder = TeamContextBuilder(db)
    generator = SocialPostGenerator(db)

    for team_id in range(1, 33):
        # Build rich context
        context = builder.build_context(dynasty_id, season, team_id, week)

        # Generate posts with context
        posts = generator.generate_game_recap_posts(
            event_type='GAME_RECAP',
            team_id=team_id,
            context=context  # Pass context to generator
        )
```

## Performance Notes

- **Caching**: Team info is cached from teams.json
- **Database Queries**: Optimized with indexes on standings, games, and transactions
- **Division/Conference Lookups**: Uses in-memory TeamIDs constants
- **Recent Activity**: Limited to 10 transactions per type to avoid performance issues

## Error Handling

```python
try:
    context = builder.build_context(dynasty_id, season, team_id, week)
except ValueError as e:
    # No standings found for team/season
    logger.error(f"Failed to build context: {e}")
```

## Testing

See `demos/validate_team_context_builder.py` for validation script:

```bash
python demos/validate_team_context_builder.py
```
