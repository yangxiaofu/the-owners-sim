# Draft Tables Migration Guide

Quick reference for applying the draft class generation database migration.

## Quick Start

### Option 1: SQLite Command Line

```bash
cd /path/to/the-owners-sim
sqlite3 data/database/nfl_simulation.db < src/database/migrations/add_draft_tables.sql
```

### Option 2: Python Script

Create a file `apply_draft_migration.py`:

```python
import sqlite3
from pathlib import Path

# Database path
db_path = Path("data/database/nfl_simulation.db")

# Migration path
migration_path = Path("src/database/migrations/add_draft_tables.sql")

# Connect to database
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys

# Read and execute migration
with open(migration_path, "r") as f:
    migration_sql = f.read()
    conn.executescript(migration_sql)

conn.commit()
conn.close()

print("✓ Migration applied successfully!")
```

Run it:
```bash
python apply_draft_migration.py
```

### Option 3: Interactive Python

```python
import sqlite3

conn = sqlite3.connect("data/database/nfl_simulation.db")
conn.execute("PRAGMA foreign_keys = ON")

with open("src/database/migrations/add_draft_tables.sql") as f:
    conn.executescript(f.read())

conn.commit()
conn.close()
```

## Verification

After applying the migration, verify it worked:

```bash
# Run the test suite
python -m pytest tests/database/test_draft_tables_migration.py -v

# Or direct execution
python tests/database/test_draft_tables_migration.py
```

## What Gets Created

### Tables
- `draft_classes` (7 columns, 2 indexes)
- `draft_prospects` (26 columns, 8 indexes)

### Total Objects
- 2 tables
- 10 indexes
- 2 unique constraints
- 3 foreign key constraints

## Common Issues

### Foreign Keys Not Working

**Problem**: Cascade deletes don't work

**Solution**: Enable foreign keys before executing migration
```sql
PRAGMA foreign_keys = ON;
```

### Migration Already Applied

**Problem**: Tables already exist

**Solution**: Migration uses `IF NOT EXISTS`, so it's safe to run multiple times

### Dependencies Missing

**Problem**: `dynasties` table doesn't exist

**Solution**: Ensure you're running against a database with the dynasties table created first

## Rollback

To remove the tables:

```sql
DROP TABLE IF EXISTS draft_prospects;
DROP TABLE IF EXISTS draft_classes;
```

**WARNING**: This will delete all draft data permanently!

## Integration with Code

After migration, you can use the tables:

```python
from src.database.api import DatabaseAPI

db = DatabaseAPI("data/database/nfl_simulation.db", dynasty_id="my_dynasty")

# Insert a draft class
db.connection.execute("""
    INSERT INTO draft_classes (draft_class_id, dynasty_id, season, total_prospects)
    VALUES (?, ?, ?, ?)
""", ("DRAFT_my_dynasty_2024", "my_dynasty", 2024, 256))

# Insert a prospect
db.connection.execute("""
    INSERT INTO draft_prospects (
        player_id, draft_class_id, dynasty_id,
        first_name, last_name, position, age,
        draft_round, draft_pick, overall, attributes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    1, "DRAFT_my_dynasty_2024", "my_dynasty",
    "John", "Doe", "QB", 21,
    1, 1, 95, '{"awareness": 90, "speed": 85}'
))

db.connection.commit()
```

## Support

For questions or issues:
1. Check `src/database/migrations/README.md` for detailed documentation
2. Review test file: `tests/database/test_draft_tables_migration.py`
3. Examine schema: `src/database/migrations/add_draft_tables.sql`
