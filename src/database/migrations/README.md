# Database Migrations

This directory contains SQL migration scripts for the NFL simulation database.

## Migration Files

### add_draft_tables.sql

**Version**: 1.0.0
**Created**: 2025-10-19
**Purpose**: Add draft class generation system tables

This migration creates two tables for managing NFL draft classes:

#### Tables Created

1. **draft_classes**: Stores metadata about generated draft classes
   - Each dynasty can have one draft class per season
   - Tracks generation date, total prospects, and status
   - Foreign key to dynasties table with cascade delete

2. **draft_prospects**: Stores individual player prospects
   - Links to draft_classes for organization
   - Supports scouting system (scouted_overall, scouting_confidence)
   - Tracks draft status (is_drafted, drafted_by_team_id, etc.)
   - Stores player attributes as JSON for flexibility
   - Development curves for player progression

#### Indexes Created

- `idx_draft_classes_dynasty`: Fast dynasty lookups
- `idx_draft_classes_season`: Season-based queries
- `idx_prospects_draft_class`: Prospect by draft class
- `idx_prospects_dynasty`: Dynasty isolation
- `idx_prospects_position`: Position filtering
- `idx_prospects_available`: Undrafted players
- `idx_prospects_overall`: Sorting by talent rating
- `idx_prospects_player_id`: Player ID lookups

#### Key Features

- **Dynasty Isolation**: Complete separation between different dynasties
- **Cascade Deletes**: Deleting a draft class removes all its prospects
- **Unique Constraints**: One draft class per dynasty per season
- **JSON Attributes**: Flexible player attribute storage
- **Scouting Support**: Hidden true ratings with scouted estimates
- **Draft Tracking**: Full audit trail of draft selections

## Running Migrations

### Using SQLite CLI

```bash
sqlite3 data/database/nfl_simulation.db < src/database/migrations/add_draft_tables.sql
```

### Using Python

```python
import sqlite3

conn = sqlite3.connect("data/database/nfl_simulation.db")

# IMPORTANT: Enable foreign keys for cascade deletes
conn.execute("PRAGMA foreign_keys = ON")

with open("src/database/migrations/add_draft_tables.sql", "r") as f:
    migration_sql = f.read()
    conn.executescript(migration_sql)

conn.commit()
conn.close()
```

## Testing Migrations

Run the migration test suite:

```bash
# Using pytest
python -m pytest tests/database/test_draft_tables_migration.py -v

# Direct execution
python tests/database/test_draft_tables_migration.py
```

The test suite validates:

- SQL syntax correctness
- Table creation success
- Index creation
- Foreign key constraints (including cascade deletes)
- Unique constraints
- Column definitions
- Data insertion and querying

## Prerequisites

- The `dynasties` table must exist before running this migration
- Foreign keys should be enabled: `PRAGMA foreign_keys = ON`

## Schema Dependencies

```
dynasties (existing)
    |
    +-- draft_classes (this migration)
            |
            +-- draft_prospects (this migration)
```

## Notes

- **Foreign Keys**: SQLite requires `PRAGMA foreign_keys = ON` for cascade deletes
- **JSON Storage**: Player attributes are stored as JSON strings for flexibility
- **Composite Primary Key**: draft_prospects uses (dynasty_id, player_id)
- **Timestamps**: Uses SQLite's CURRENT_TIMESTAMP for automatic timestamps
- **BOOLEAN**: SQLite stores booleans as INTEGER (0/1)

## Migration History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-10-19 | Initial draft tables creation |
