import sqlite3
import random

def seed_sample_data(db_path: str = "data/football_sim.db") -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM teams")
        if cursor.fetchone()[0] > 0:
            print("Sample data already exists")
            return
        
        # Sample teams
        teams = [
            ("Bears", "Chicago", "CHI", "NFC", "North", 1920),
            ("Packers", "Green Bay", "GB", "NFC", "North", 1919),
            ("Lions", "Detroit", "DET", "NFC", "North", 1930),
            ("Vikings", "Minneapolis", "MIN", "NFC", "North", 1961),
            ("Cowboys", "Dallas", "DAL", "NFC", "East", 1960),
            ("Eagles", "Philadelphia", "PHI", "NFC", "East", 1933),
            ("Giants", "New York", "NYG", "NFC", "East", 1925),
            ("Commanders", "Washington", "WSH", "NFC", "East", 1932)
        ]
        
        # Insert teams
        for team in teams:
            cursor.execute("""
                INSERT INTO teams (name, city, abbreviation, conference, division, founded_year, salary_cap_space)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (*team, random.randint(10000000, 50000000)))
        
        # Get team IDs for players
        cursor.execute("SELECT id FROM teams")
        team_ids = [row[0] for row in cursor.fetchall()]
        
        # Sample players for each team
        positions = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K", "P"]
        first_names = ["John", "Mike", "David", "Chris", "Matt", "Tom", "Aaron", "Josh", "Ryan", "Alex"]
        last_names = ["Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Wilson"]
        
        for team_id in team_ids:
            # Add 25 players per team
            for i in range(25):
                position = random.choice(positions)
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                
                cursor.execute("""
                    INSERT INTO players (first_name, last_name, position, jersey_number, team_id, 
                                       age, height, weight, years_pro, injury_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'healthy')
                """, (first_name, last_name, position, i+1, team_id, 
                      random.randint(22, 35), random.randint(68, 78), 
                      random.randint(180, 320), random.randint(0, 12)))
                
                player_id = cursor.lastrowid
                
                # Add player attributes
                cursor.execute("""
                    INSERT INTO player_attributes (player_id, speed, strength, agility, stamina,
                                                 football_iq, work_ethic, leadership, overall_rating, potential)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (player_id, 
                      random.randint(30, 90), random.randint(30, 90),
                      random.randint(30, 90), random.randint(30, 90),
                      random.randint(30, 90), random.randint(30, 90),
                      random.randint(30, 90), random.randint(40, 85),
                      random.randint(50, 95)))
        
        # Add current season
        cursor.execute("INSERT INTO seasons (year, salary_cap, is_active, current_week) VALUES (2024, 224800000, 1, 1)")
        
        conn.commit()
        print("Sample data seeded successfully!")
        print(f"Added {len(teams)} teams with 25 players each")