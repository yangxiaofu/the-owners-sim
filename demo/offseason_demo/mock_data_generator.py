"""
Mock Data Generator for Offseason UI Demo

Generates fixture data for testing the offseason UI without requiring a full
season simulation. Creates realistic mock data for all 32 NFL teams including:
- Team roster data (5-10 players per team)
- Contract data with position-based salaries
- Salary cap data (~$200M cap with realistic usage)

All data is deterministic for consistent testing.
"""

import sqlite3
import random
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

# Import TeamIDs for real team data
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from constants.team_ids import TeamIDs
from database.connection import DatabaseConnection


# Position definitions with realistic salary ranges
POSITION_CONFIG = {
    "QB": {
        "count_range": (2, 3),
        "salary_range": (1_000_000, 50_000_000),
        "avg_salary": 25_000_000,
    },
    "RB": {
        "count_range": (2, 3),
        "salary_range": (800_000, 15_000_000),
        "avg_salary": 5_000_000,
    },
    "WR": {
        "count_range": (2, 3),
        "salary_range": (900_000, 25_000_000),
        "avg_salary": 10_000_000,
    },
    "TE": {
        "count_range": (1, 2),
        "salary_range": (800_000, 18_000_000),
        "avg_salary": 6_000_000,
    },
    "OL": {
        "count_range": (1, 2),
        "salary_range": (850_000, 20_000_000),
        "avg_salary": 8_000_000,
    },
    "DL": {
        "count_range": (1, 2),
        "salary_range": (900_000, 22_000_000),
        "avg_salary": 9_000_000,
    },
    "LB": {
        "count_range": (1, 2),
        "salary_range": (850_000, 18_000_000),
        "avg_salary": 7_000_000,
    },
    "DB": {
        "count_range": (1, 2),
        "salary_range": (900_000, 20_000_000),
        "avg_salary": 8_000_000,
    },
    "K": {
        "count_range": (1, 1),
        "salary_range": (1_000_000, 6_000_000),
        "avg_salary": 2_500_000,
    },
    "P": {
        "count_range": (1, 1),
        "salary_range": (900_000, 4_000_000),
        "avg_salary": 1_800_000,
    },
}


def get_team_name(team_id: int) -> str:
    """Get team full name from team ID."""
    # Map team IDs to names using a simple lookup
    team_names = {
        1: "Buffalo Bills", 2: "Miami Dolphins", 3: "New England Patriots", 4: "New York Jets",
        5: "Baltimore Ravens", 6: "Cincinnati Bengals", 7: "Cleveland Browns", 8: "Pittsburgh Steelers",
        9: "Houston Texans", 10: "Indianapolis Colts", 11: "Jacksonville Jaguars", 12: "Tennessee Titans",
        13: "Denver Broncos", 14: "Kansas City Chiefs", 15: "Las Vegas Raiders", 16: "Los Angeles Chargers",
        17: "Dallas Cowboys", 18: "New York Giants", 19: "Philadelphia Eagles", 20: "Washington Commanders",
        21: "Chicago Bears", 22: "Detroit Lions", 23: "Green Bay Packers", 24: "Minnesota Vikings",
        25: "Atlanta Falcons", 26: "Carolina Panthers", 27: "New Orleans Saints", 28: "Tampa Bay Buccaneers",
        29: "Arizona Cardinals", 30: "Los Angeles Rams", 31: "San Francisco 49ers", 32: "Seattle Seahawks",
    }
    return team_names.get(team_id, f"Team {team_id}")


def generate_player_name(team_id: int, position: str, index: int) -> Tuple[str, str]:
    """
    Generate deterministic player name.

    Returns:
        Tuple of (first_name, last_name)
    """
    team_abbr = get_team_name(team_id).split()[-1]  # Get last word (e.g., "Bills", "Cowboys")
    return (team_abbr, f"{position}{index + 1}")


def generate_contract_years(position: str, salary: int) -> int:
    """Generate contract length based on position and salary."""
    if position in ["K", "P"]:
        return random.choice([1, 2, 3])
    elif salary > 30_000_000:
        return random.choice([4, 5, 6])
    elif salary > 15_000_000:
        return random.choice([3, 4, 5])
    elif salary > 5_000_000:
        return random.choice([2, 3, 4])
    else:
        return random.choice([1, 2, 3])


def generate_salary(position: str, seed: int) -> int:
    """
    Generate deterministic salary for a position.

    Uses seed for deterministic randomness while maintaining realistic distributions.
    """
    config = POSITION_CONFIG[position]
    random.seed(seed)

    # Use weighted distribution towards average
    min_sal, max_sal = config["salary_range"]
    avg_sal = config["avg_salary"]

    # 60% chance of being near average, 40% chance of extremes
    if random.random() < 0.6:
        # Within 50% of average
        variation = int(avg_sal * 0.5)
        salary = random.randint(avg_sal - variation, avg_sal + variation)
    else:
        # Full range
        salary = random.randint(min_sal, max_sal)

    # Clamp to range
    salary = max(min_sal, min(max_sal, salary))

    return salary


def generate_team_roster(
    team_id: int,
    dynasty_id: str,
    current_season: int
) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate mock roster and contracts for a team.

    Returns:
        Tuple of (players_data, contracts_data)
    """
    players = []
    contracts = []
    player_id_counter = team_id * 100  # Ensure unique player IDs per team

    for position, config in POSITION_CONFIG.items():
        count = random.Random(team_id * 100 + hash(position)).choice(
            range(config["count_range"][0], config["count_range"][1] + 1)
        )

        for i in range(count):
            player_id = player_id_counter
            player_id_counter += 1

            first_name, last_name = generate_player_name(team_id, position, i)

            # Generate salary
            seed = team_id * 10000 + player_id
            salary = generate_salary(position, seed)

            # Generate contract details
            contract_years = generate_contract_years(position, salary)
            total_value = salary * contract_years
            signing_bonus = int(total_value * random.Random(seed).uniform(0.1, 0.3))
            signing_bonus_proration = signing_bonus // contract_years

            # Player data
            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "number": (i + 1) * 10 + (team_id % 10),  # Pseudo-realistic number
                "team_id": team_id,
                "position": position,
                "dynasty_id": dynasty_id,
            }
            players.append(player_data)

            # Contract data
            contract_data = {
                "player_id": player_id,
                "team_id": team_id,
                "dynasty_id": dynasty_id,
                "start_year": current_season,
                "end_year": current_season + contract_years - 1,
                "contract_years": contract_years,
                "contract_type": "VETERAN",
                "total_value": total_value,
                "signing_bonus": signing_bonus,
                "signing_bonus_proration": signing_bonus_proration,
                "guaranteed_at_signing": int(total_value * random.Random(seed + 1).uniform(0.3, 0.6)),
                "injury_guaranteed": 0,
                "total_guaranteed": int(total_value * random.Random(seed + 1).uniform(0.3, 0.6)),
                "is_active": True,
                "signed_date": f"{current_season}-03-15",
            }
            contracts.append(contract_data)

            # Generate contract year details for each year
            for year_idx in range(contract_years):
                year_salary = salary + int(salary * 0.05 * year_idx)  # Small escalation

    return players, contracts


def generate_cap_data(
    team_id: int,
    dynasty_id: str,
    current_season: int,
    contracts: List[Dict]
) -> Dict:
    """
    Generate salary cap data for a team.

    Returns:
        Cap data dictionary
    """
    # Calculate total cap hit from contracts
    total_cap_hit = sum(
        c["signing_bonus_proration"] + (c["total_value"] - c["signing_bonus"]) // c["contract_years"]
        for c in contracts
    )

    # Add some randomness to cap usage (85-95% of cap)
    salary_cap = 255_400_000  # 2024 NFL cap
    random.seed(team_id * 1000)
    usage_pct = random.uniform(0.85, 0.95)
    total_cap_hit = int(salary_cap * usage_pct)

    return {
        "team_id": team_id,
        "season": current_season,
        "dynasty_id": dynasty_id,
        "salary_cap_limit": salary_cap,
        "carryover_from_previous": random.randint(-5_000_000, 10_000_000),
        "active_contracts_total": total_cap_hit,
        "dead_money_total": random.randint(0, 15_000_000),
        "ltbe_incentives_total": random.randint(0, 5_000_000),
        "practice_squad_total": 0,
        "is_top_51_active": True,
        "top_51_total": total_cap_hit,
        "cash_spent_this_year": total_cap_hit,
    }


def insert_players(conn: sqlite3.Connection, players: List[Dict]) -> None:
    """Insert player data into database."""
    conn.executemany(
        """
        INSERT INTO players (
            dynasty_id, player_id, first_name, last_name, number, team_id,
            positions, attributes, status, years_pro
        ) VALUES (
            :dynasty_id, :player_id, :first_name, :last_name, :number, :team_id,
            json_array(:position), '{"overall": 75}', 'active', 3
        )
        """,
        players
    )


def insert_contracts(conn: sqlite3.Connection, contracts: List[Dict]) -> None:
    """Insert contract data into database."""
    conn.executemany(
        """
        INSERT INTO player_contracts (
            player_id, team_id, dynasty_id, start_year, end_year, contract_years,
            contract_type, total_value, signing_bonus, signing_bonus_proration,
            guaranteed_at_signing, injury_guaranteed, total_guaranteed,
            is_active, signed_date
        ) VALUES (
            :player_id, :team_id, :dynasty_id, :start_year, :end_year, :contract_years,
            :contract_type, :total_value, :signing_bonus, :signing_bonus_proration,
            :guaranteed_at_signing, :injury_guaranteed, :total_guaranteed,
            :is_active, :signed_date
        )
        """,
        contracts
    )


def insert_team_rosters(conn: sqlite3.Connection, players: List[Dict]) -> None:
    """
    Insert team roster records linking players to teams.

    The team_rosters table is required by PlayerRosterAPI for roster queries.
    """
    roster_records = [
        {
            "dynasty_id": p["dynasty_id"],
            "team_id": p["team_id"],
            "player_id": p["player_id"],
            "roster_status": "active",  # All mock players are on active roster
        }
        for p in players
    ]

    conn.executemany(
        """
        INSERT INTO team_rosters (dynasty_id, team_id, player_id, roster_status)
        VALUES (:dynasty_id, :team_id, :player_id, :roster_status)
        """,
        roster_records
    )


def insert_cap_data(conn: sqlite3.Connection, cap_records: List[Dict]) -> None:
    """
    Insert salary cap data into database.

    Note: Creates team_salary_cap table if it doesn't exist (not in base schema).
    """
    # Create table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_salary_cap (
            cap_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            dynasty_id TEXT NOT NULL,
            salary_cap_limit INTEGER NOT NULL,
            carryover_from_previous INTEGER DEFAULT 0,
            active_contracts_total INTEGER DEFAULT 0,
            dead_money_total INTEGER DEFAULT 0,
            ltbe_incentives_total INTEGER DEFAULT 0,
            practice_squad_total INTEGER DEFAULT 0,
            is_top_51_active BOOLEAN DEFAULT TRUE,
            top_51_total INTEGER DEFAULT 0,
            cash_spent_this_year INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(team_id, season, dynasty_id)
        )
    """)

    conn.executemany(
        """
        INSERT OR REPLACE INTO team_salary_cap (
            team_id, season, dynasty_id, salary_cap_limit, carryover_from_previous,
            active_contracts_total, dead_money_total, ltbe_incentives_total,
            practice_squad_total, is_top_51_active, top_51_total, cash_spent_this_year
        ) VALUES (
            :team_id, :season, :dynasty_id, :salary_cap_limit, :carryover_from_previous,
            :active_contracts_total, :dead_money_total, :ltbe_incentives_total,
            :practice_squad_total, :is_top_51_active, :top_51_total, :cash_spent_this_year
        )
        """,
        cap_records
    )


def generate_mock_data(
    database_path: str,
    dynasty_id: str = "ui_offseason_demo",
    current_season: int = 2025
) -> Dict[str, int]:
    """
    Generate all mock data for offseason demo.

    Creates:
    - 32 NFL teams
    - 5-10 players per team (varied by position)
    - Contracts for all players
    - Salary cap data for all teams

    Args:
        database_path: Path to SQLite database
        dynasty_id: Dynasty identifier for data isolation
        current_season: Current season year

    Returns:
        Dict with counts: {"teams": 32, "players": X, "contracts": X}
    """
    # Ensure database directory exists
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    # Initialize database schema
    db_conn = DatabaseConnection(database_path)
    db_conn.initialize_database()

    # Connect to database
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row

    try:
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys=ON")

        # Create dynasty if it doesn't exist
        conn.execute(
            """
            INSERT OR IGNORE INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
            VALUES (?, ?, ?, NULL)
            """,
            (dynasty_id, "Offseason UI Demo", "Demo User")
        )

        all_players = []
        all_contracts = []
        all_cap_records = []

        # Generate data for all 32 teams
        for team_id in range(1, 33):
            players, contracts = generate_team_roster(team_id, dynasty_id, current_season)
            cap_data = generate_cap_data(team_id, dynasty_id, current_season, contracts)

            all_players.extend(players)
            all_contracts.extend(contracts)
            all_cap_records.append(cap_data)

        # Insert all data in batches
        print(f"Inserting {len(all_players)} players...")
        insert_players(conn, all_players)

        print(f"Inserting {len(all_contracts)} contracts...")
        insert_contracts(conn, all_contracts)

        print(f"Inserting {len(all_players)} roster records...")
        insert_team_rosters(conn, all_players)

        print(f"Inserting {len(all_cap_records)} cap records...")
        insert_cap_data(conn, all_cap_records)

        conn.commit()

        return {
            "teams": 32,
            "players": len(all_players),
            "contracts": len(all_contracts),
            "cap_records": len(all_cap_records),
        }

    except Exception as e:
        conn.rollback()
        print(f"Error generating mock data: {e}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    """Run mock data generation for testing."""
    import os

    # Use demo database path
    db_path = "demo/offseason_demo/offseason_demo.db"

    print("Generating mock offseason data...")
    print(f"Database: {db_path}")
    print(f"Dynasty: ui_offseason_demo")
    print("-" * 60)

    # Generate mock data
    counts = generate_mock_data(db_path)

    print("\nMock data generated successfully!")
    print(f"  Teams: {counts['teams']}")
    print(f"  Players: {counts['players']}")
    print(f"  Contracts: {counts['contracts']}")
    print(f"  Cap Records: {counts['cap_records']}")
    print(f"\nDatabase created at: {os.path.abspath(db_path)}")
