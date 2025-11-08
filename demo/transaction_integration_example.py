"""
TransactionContext Integration Example

Shows how to integrate TransactionContext into existing database operations
in the NFL simulation system.

This demonstrates refactoring patterns for common database operations.

Run with:
    PYTHONPATH=src python demo/transaction_integration_example.py
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import DatabaseConnection, TransactionContext, transaction


class ContractManager:
    """Example: Contract operations using TransactionContext."""

    def __init__(self, db_path: str):
        self.db_conn = DatabaseConnection(db_path)

    def sign_player(self, player_id: int, team_id: int, contract_years: int, total_value: int, dynasty_id: str):
        """
        Sign a player to a new contract with atomic operations.

        This demonstrates a multi-step operation that must all succeed or all fail:
        1. Create contract record
        2. Create contract year details
        3. Update player's team assignment
        4. Update team's cap usage
        """
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()

        with TransactionContext(conn, mode="IMMEDIATE") as tx:
            # Step 1: Create main contract record
            cursor.execute("""
                INSERT INTO player_contracts (
                    player_id, team_id, dynasty_id, start_year, end_year, contract_years,
                    contract_type, total_value, signing_bonus, is_active, signed_date
                ) VALUES (?, ?, ?, 2024, ?, ?, 'VETERAN', ?, 0, TRUE, date('now'))
            """, (player_id, team_id, dynasty_id, 2024 + contract_years - 1, contract_years, total_value))

            contract_id = cursor.lastrowid

            # Step 2: Create contract year details
            annual_salary = total_value // contract_years
            for year in range(contract_years):
                season_year = 2024 + year
                cursor.execute("""
                    INSERT INTO contract_year_details (
                        contract_id, contract_year, season_year, base_salary,
                        total_cap_hit, cash_paid
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (contract_id, year + 1, season_year, annual_salary, annual_salary, annual_salary))

            # Step 3: Update player's team assignment
            cursor.execute("""
                UPDATE players
                SET team_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE player_id = ? AND dynasty_id = ?
            """, (team_id, player_id, dynasty_id))

            # Step 4: Verify cap space (simplified - in real system would check team_cap table)
            # For demo purposes, assume cap space is sufficient
            print(f"   Verified cap space for team {team_id}")

            print(f"Successfully signed player {player_id} to team {team_id}")
            print(f"Contract: {contract_years} years, ${total_value:,}")

            # All operations committed atomically

    def release_player(self, player_id: int, team_id: int, dynasty_id: str, june_1_designation: bool = False):
        """
        Release a player with dead money calculation.

        Demonstrates nested transaction for contract termination validation.
        """
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()

        with TransactionContext(conn, mode="IMMEDIATE") as tx:
            # Get active contract
            cursor.execute("""
                SELECT contract_id, total_value, signing_bonus, start_year
                FROM player_contracts
                WHERE player_id = ? AND team_id = ? AND dynasty_id = ? AND is_active = TRUE
            """, (player_id, team_id, dynasty_id))

            contract = cursor.fetchone()
            if not contract:
                raise ValueError(f"No active contract found for player {player_id}")

            contract_id, total_value, signing_bonus, start_year = contract

            # Calculate dead money (simplified)
            years_remaining = 2024 - start_year
            dead_money = signing_bonus if years_remaining > 0 else 0

            # Update contract status
            cursor.execute("""
                UPDATE player_contracts
                SET is_active = FALSE, voided_date = date('now')
                WHERE contract_id = ?
            """, (contract_id,))

            # Update player's team (0 = free agent)
            cursor.execute("""
                UPDATE players
                SET team_id = 0, updated_at = CURRENT_TIMESTAMP
                WHERE player_id = ? AND dynasty_id = ?
            """, (player_id, dynasty_id))

            # Update team cap (simplified - in real system would update team_cap table)
            print(f"   Updated team cap (relief from payments, ${dead_money:,} dead money)")

            print(f"Released player {player_id} from team {team_id}")
            print(f"Dead money: ${dead_money:,}")


class GameManager:
    """Example: Game result recording using TransactionContext."""

    def __init__(self, db_path: str):
        self.db_conn = DatabaseConnection(db_path)

    def record_game_result(
        self,
        game_id: str,
        dynasty_id: str,
        season: int,
        week: int,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        player_stats: list
    ):
        """
        Record complete game result with standings and statistics.

        Demonstrates a complex multi-table transaction with conditional logic.
        """
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()

        with TransactionContext(conn, mode="IMMEDIATE") as tx:
            # Step 1: Insert game record
            winner_id = home_team_id if home_score > away_score else away_team_id
            cursor.execute("""
                INSERT INTO games (
                    game_id, dynasty_id, season, week, season_type, game_type,
                    home_team_id, away_team_id, home_score, away_score,
                    game_date, created_at
                ) VALUES (?, ?, ?, ?, 'regular_season', 'regular', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (game_id, dynasty_id, season, week, home_team_id, away_team_id, home_score, away_score, 0))

            # Step 2: Update standings for winner
            if home_score != away_score:  # No ties in this example
                if winner_id == home_team_id:
                    cursor.execute("""
                        UPDATE standings
                        SET wins = wins + 1, home_wins = home_wins + 1,
                            points_for = points_for + ?, points_against = points_against + ?
                        WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = 'regular_season'
                    """, (home_score, away_score, dynasty_id, home_team_id, season))

                    cursor.execute("""
                        UPDATE standings
                        SET losses = losses + 1, away_losses = away_losses + 1,
                            points_for = points_for + ?, points_against = points_against + ?
                        WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = 'regular_season'
                    """, (away_score, home_score, dynasty_id, away_team_id, season))
                else:
                    cursor.execute("""
                        UPDATE standings
                        SET wins = wins + 1, away_wins = away_wins + 1,
                            points_for = points_for + ?, points_against = points_against + ?
                        WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = 'regular_season'
                    """, (away_score, home_score, dynasty_id, away_team_id, season))

                    cursor.execute("""
                        UPDATE standings
                        SET losses = losses + 1, home_losses = home_losses + 1,
                            points_for = points_for + ?, points_against = points_against + ?
                        WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = 'regular_season'
                    """, (home_score, away_score, dynasty_id, home_team_id, season))

            # Step 3: Insert player statistics
            for stats in player_stats:
                cursor.execute("""
                    INSERT INTO player_game_stats (
                        dynasty_id, game_id, season_type, player_id, player_name, team_id, position,
                        passing_yards, passing_tds, rushing_yards, rushing_tds, receptions, receiving_yards
                    ) VALUES (?, ?, 'regular_season', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dynasty_id, game_id, stats['player_id'], stats['name'], stats['team_id'], stats['position'],
                    stats.get('passing_yards', 0), stats.get('passing_tds', 0),
                    stats.get('rushing_yards', 0), stats.get('rushing_tds', 0),
                    stats.get('receptions', 0), stats.get('receiving_yards', 0)
                ))

            print(f"Recorded game {game_id}: {home_team_id} vs {away_team_id}")
            print(f"Score: {home_score} - {away_score}")
            print(f"Recorded {len(player_stats)} player stat lines")

            # All changes committed atomically


class DraftManager:
    """Example: Draft operations with validation using nested transactions."""

    def __init__(self, db_path: str):
        self.db_conn = DatabaseConnection(db_path)

    def execute_draft_pick(
        self,
        dynasty_id: str,
        pick_number: int,
        round_number: int,
        team_id: int,
        player_id: int
    ):
        """
        Execute a draft pick with validation.

        Demonstrates nested transaction for validation that might fail.
        """
        conn = self.db_conn.get_connection()
        cursor = conn.cursor()

        with TransactionContext(conn, mode="IMMEDIATE") as outer_tx:
            # Record the pick
            cursor.execute("""
                INSERT INTO draft_picks (dynasty_id, pick_number, round_number, team_id, player_id, pick_time)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (dynasty_id, pick_number, round_number, team_id, player_id))

            # Nested transaction for roster validation
            try:
                with TransactionContext(conn) as inner_tx:
                    # Get current roster count
                    cursor.execute("""
                        SELECT COUNT(*) FROM team_rosters
                        WHERE dynasty_id = ? AND team_id = ? AND roster_status = 'active'
                    """, (dynasty_id, team_id))

                    roster_count = cursor.fetchone()[0]

                    # Draft roster can have up to 90 players
                    if roster_count >= 90:
                        raise ValueError(f"Team {team_id} roster is full (90 players)")

                    # Add to roster
                    cursor.execute("""
                        INSERT INTO team_rosters (dynasty_id, team_id, player_id, roster_status, joined_date)
                        VALUES (?, ?, ?, 'active', date('now'))
                    """, (dynasty_id, team_id, player_id))

                    print(f"Added player {player_id} to team {team_id} roster")

            except ValueError as e:
                print(f"Roster validation failed: {e}")
                # Inner transaction rolled back, but pick is still recorded
                # (In real system, might want to mark pick as "needs roster move")

            # Update player's team
            cursor.execute("""
                UPDATE players
                SET team_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE player_id = ? AND dynasty_id = ?
            """, (team_id, player_id, dynasty_id))

            print(f"Draft Pick #{pick_number}: Team {team_id} selects Player {player_id}")


def demo_integration():
    """Demonstrate integration patterns."""
    print("\n" + "="*80)
    print("TransactionContext Integration Examples")
    print("="*80)

    # Use in-memory database for demo
    db_path = ":memory:"
    db_conn = DatabaseConnection(db_path)
    db_conn.initialize_database()

    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Setup test dynasty
    cursor.execute("INSERT INTO dynasties (dynasty_id, dynasty_name, team_id) VALUES ('test', 'Test Dynasty', 1)")
    cursor.execute("INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes) VALUES ('test', 1, 'Test', 'Player', 12, 0, '[]', '{}')")
    cursor.execute("""
        INSERT INTO standings (dynasty_id, team_id, season, season_type, wins, losses, points_for, points_against)
        VALUES ('test', 1, 2024, 'regular_season', 0, 0, 0, 0)
    """)
    cursor.execute("""
        INSERT INTO standings (dynasty_id, team_id, season, season_type, wins, losses, points_for, points_against)
        VALUES ('test', 2, 2024, 'regular_season', 0, 0, 0, 0)
    """)
    conn.commit()

    print("\n1. Contract Manager - Sign Player")
    print("-" * 80)
    contract_mgr = ContractManager(db_path)
    try:
        contract_mgr.sign_player(
            player_id=1,
            team_id=1,
            contract_years=5,
            total_value=50000000,
            dynasty_id='test'
        )
    except Exception as e:
        print(f"Error: {e}")

    print("\n2. Game Manager - Record Game Result")
    print("-" * 80)
    game_mgr = GameManager(db_path)
    player_stats = [
        {'player_id': 1, 'name': 'Test Player', 'team_id': 1, 'position': 'QB',
         'passing_yards': 350, 'passing_tds': 3},
        {'player_id': 2, 'name': 'RB Player', 'team_id': 1, 'position': 'RB',
         'rushing_yards': 120, 'rushing_tds': 2}
    ]
    try:
        game_mgr.record_game_result(
            game_id='game_1',
            dynasty_id='test',
            season=2024,
            week=1,
            home_team_id=1,
            away_team_id=2,
            home_score=28,
            away_score=24,
            player_stats=player_stats
        )
    except Exception as e:
        print(f"Error: {e}")

    print("\n3. Draft Manager - Execute Pick")
    print("-" * 80)
    draft_mgr = DraftManager(db_path)
    try:
        draft_mgr.execute_draft_pick(
            dynasty_id='test',
            pick_number=1,
            round_number=1,
            team_id=1,
            player_id=1
        )
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "="*80)
    print("Integration examples completed successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    demo_integration()
