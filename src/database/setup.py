import sqlite3
import os
from pathlib import Path

def initialize_database(db_path: str = "data/football_sim.db") -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    migration_path = os.path.join(os.path.dirname(__file__), 'migrations', '001_initial_schema.sql')
    
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
    
    with sqlite3.connect(db_path) as conn:
        for statement in statements:
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    raise e
        conn.commit()
    
    print(f"Database initialized at: {db_path}")

def database_exists(db_path: str = "data/football_sim.db") -> bool:
    return os.path.exists(db_path)

def check_tables_exist(db_path: str = "data/football_sim.db") -> bool:
    if not database_exists(db_path):
        return False
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teams'")
        return cursor.fetchone() is not None