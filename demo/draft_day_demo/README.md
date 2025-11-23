# Draft Day Demo

Interactive NFL draft simulation where you control a randomly-assigned team.

## Features
- Random team assignment
- Manual player selection on your picks
- AI teams auto-select using GM archetypes
- Auto-sim to skip CPU picks
- Real-time draft board updates

## Running the Demo

### Standalone
```bash
python demo/draft_day_demo/draft_day_demo.py
```

### From Main Application
1. Launch main.py
2. Click Tools → Draft Day Demo

## Controls
- **Make Pick**: Select prospect and draft (your turn only)
- **Auto-Sim to My Next Pick**: Fast-forward through CPU picks

## Database
- Location: `demo/draft_day_demo/draft_demo.db`
- Reset: Delete file to regenerate

## How It Works
1. 224 prospects generated (7 rounds × 32 teams)
2. Draft order based on team records (worst picks first)
3. AI teams use position needs + GM personality
4. All picks transacted to players table

## What You'll See

### Draft Board
- All 224 prospects sorted by overall rating
- Color-coded by position
- Real-time updates as picks are made

### Your Picks
- Dialog prompts when it's your turn
- Select from available prospects
- Make your pick to continue draft

### AI Behavior
- Teams evaluate based on:
  - Position needs (roster gaps)
  - GM archetype (aggressive vs conservative)
  - Best player available vs need
  - Value vs draft position

### Draft Flow
1. Round 1: All 32 teams pick (worst to best)
2. Round 2: Same order repeats
3. Rounds 3-7: Continue until pick 224

## Technical Details

### Database Schema
- `draft_prospects`: 224 generated players with ratings
- `draft_picks`: 224 picks with team assignments
- `draft_board`: Tracks pick transactions
- `players`: Final drafted player rosters

### Draft Order Logic
- Based on regular season records (wins/losses)
- Playoff teams pick last (by playoff finish)
- Non-playoff teams pick first (by record)

### AI Decision Engine
- `DraftAIService`: Evaluates prospects for each team
- Position scoring based on roster depth
- GM personality modifiers (risk tolerance, BPA vs need)
- Context-aware need calculation

## Customization

### Change Your Team
Edit the random assignment in `draft_day_demo.py`:
```python
# Instead of random selection
user_team_id = random.randint(1, 32)

# Pick specific team (e.g., Detroit Lions = 22)
user_team_id = 22
```

### Regenerate Prospects
Delete `draft_demo.db` and run again for new draft class.

### Adjust Draft Class Quality
Modify prospect generation in `setup_draft_database.py`:
- Change overall rating ranges
- Adjust position distributions
- Modify trait correlations

## Troubleshooting

### Database Not Found
If the demo doesn't auto-create the database:
```bash
cd demo/draft_day_demo
python setup_draft_database.py
```

### Import Errors
Ensure you're running from project root:
```bash
# From project root
python demo/draft_day_demo/draft_day_demo.py
```

### UI Not Loading
Check PySide6 installation:
```bash
pip install -r requirements-ui.txt
```

## Demo Limitations

This is a standalone demo with simplified systems:
- Mock team rosters (not from real dynasty)
- Fixed 2025 season year
- No salary cap constraints
- No contract negotiations
- Isolated database (doesn't affect main app)

For full draft functionality, use the main application's offseason system.
