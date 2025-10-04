# Running the Full Season Demo

Quick reference for running the full season simulation.

## From the Demo Directory

```bash
# Navigate to the demo
cd demo/full_season_demo

# Run the simulation
PYTHONPATH=../../src python full_season_sim.py
```

## From the Project Root

```bash
# Alternative method from project root
PYTHONPATH=src python demo/full_season_demo/full_season_sim.py
```

## What to Expect

1. **Dynasty Creation Prompt**:
   ```
   Enter dynasty ID: my_dynasty
   Enter dynasty name: Championship Run 2024
   Enter your name: [Your Name]
   Select team (optional): 22 (Detroit Lions)
   ```

2. **Interactive Menu**:
   ```
   ================================================================================
                                FULL SEASON SIMULATION
   ================================================================================
   Current Phase: REGULAR_SEASON
   Current Date: September 5, 2024
   Dynasty: Championship Run 2024
   Season: 2024

   Options:
     1 - Advance 1 day
     2 - Advance 1 week
     3 - View current standings
     4 - View upcoming games
     5 - View playoff picture (Week 10+)
     8 - Simulate to end
     0 - Quit

   Select option:
   ```

3. **Simulation Progress**:
   - Regular season: 272 games over 18 weeks
   - Automatic playoff transition with seeding display
   - Playoffs: 13 games over 4 rounds
   - Offseason: Final summary and stat leaders

## Quick Commands

| What You Want | Command |
|---------------|---------|
| Simulate one week | Enter `2` |
| View standings | Enter `3` |
| See playoff picture | Enter `5` (Week 10+) |
| Fast-forward to end | Enter `8` |
| View playoff bracket | Enter `6` (during playoffs) |
| Exit and save | Enter `0` |

## Database Location

Your simulation data is saved to:
```
demo/full_season_demo/data/full_season_[your_dynasty_id].db
```

## Querying the Database

```bash
# Open your dynasty database
cd demo/full_season_demo/data
sqlite3 full_season_[your_dynasty_id].db

# Example queries
.mode column
.headers on

-- View all playoff games
SELECT * FROM games WHERE season_type = 'playoffs';

-- Regular season passing leaders
SELECT player_name, SUM(passing_yards) as yards
FROM player_game_stats
WHERE season_type = 'regular_season'
GROUP BY player_id
ORDER BY yards DESC
LIMIT 10;
```

## Troubleshooting

### Error: "No module named 'src'"
**Solution**: Make sure to set `PYTHONPATH=../../src` (from demo directory) or `PYTHONPATH=src` (from project root)

### Error: "Database file not found"
**Solution**: The `data/` directory is created automatically on first run. If missing, run:
```bash
mkdir -p demo/full_season_demo/data
```

### Want to start over?
Delete the database file and run again:
```bash
rm demo/full_season_demo/data/full_season_[your_dynasty_id].db
PYTHONPATH=../../src python full_season_sim.py
```

## See Also

- **Full Documentation**: [README.md](README.md)
- **Implementation Plan**: `/docs/plans/full_season_simulation_plan.md`
- **Database Schema**: `/docs/schema/database_schema.md`
