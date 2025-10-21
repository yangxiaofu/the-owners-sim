"""
Offseason Transaction Workflow Example

Demonstrates TransactionLogger integration with event system following
the Event-Cap Bridge pattern.

This example shows:
1. Creating a TransactionLogger instance
2. Injecting logger into events (optional pattern)
3. Automatic transaction logging after event execution
4. Querying transaction history

Usage:
    PYTHONPATH=src python demo/transaction_logging_demo/offseason_transaction_workflow.py
"""

from datetime import date
from calendar.date_models import Date
from persistence.transaction_logger import TransactionLogger
from events.free_agency_events import UFASigningEvent
from events.draft_events import DraftPickEvent
from events.contract_events import PlayerReleaseEvent


class OffseasonTransactionWorkflow:
    """
    Domain model demonstrating transaction logging integration.

    Follows Event-Cap Bridge pattern:
    - Logger is optional dependency
    - Events execute independently
    - Logging happens after successful execution
    """

    def __init__(self, database_path: str, dynasty_id: str, season: int):
        """
        Initialize offseason workflow with transaction logging.

        Args:
            database_path: Path to database
            dynasty_id: Dynasty context
            season: Current season year
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize transaction logger (optional)
        self.transaction_logger = TransactionLogger(database_path)

    def execute_free_agency_signing(
        self,
        team_id: int,
        player_id: str,
        contract_years: int,
        contract_value: int,
        signing_bonus: int,
        base_salaries: list,
        guaranteed_amounts: list,
        signing_date: date
    ):
        """
        Execute UFA signing with automatic transaction logging.

        Args:
            team_id: Team signing the player
            player_id: Player being signed
            contract_years: Contract length in years
            contract_value: Total contract value
            signing_bonus: Signing bonus amount
            base_salaries: Year-by-year base salaries
            guaranteed_amounts: Year-by-year guaranteed amounts
            signing_date: Date of signing

        Returns:
            EventResult from signing execution
        """
        print(f"\n{'=' * 60}")
        print(f"EXECUTING FREE AGENCY SIGNING")
        print(f"{'=' * 60}")
        print(f"Team: {team_id}")
        print(f"Player: {player_id}")
        print(f"Contract: {contract_years}yr / ${contract_value:,}")
        print(f"Dynasty: {self.dynasty_id}")

        # Create event with transaction logger injected
        event = UFASigningEvent(
            team_id=team_id,
            player_id=player_id,
            contract_years=contract_years,
            contract_value=contract_value,
            signing_bonus=signing_bonus,
            base_salaries=base_salaries,
            guaranteed_amounts=guaranteed_amounts,
            season=self.season,
            event_date=Date.from_python_date(signing_date),
            dynasty_id=self.dynasty_id,
            database_path=self.database_path,
            transaction_logger=self.transaction_logger  # INJECT LOGGER
        )

        # Execute event (transaction logging happens automatically if successful)
        result = event.simulate()

        if result.success:
            print(f"\nSUCCESS: {result.data.get('message')}")
            print(f"Contract ID: {result.data.get('contract_id')}")
            print(f"Cap Impact: ${result.data.get('cap_impact'):,}")
            print(f"Transaction logged automatically")
        else:
            print(f"\nFAILED: {result.error_message}")

        return result

    def execute_draft_pick(
        self,
        team_id: int,
        round_number: int,
        pick_number: int,
        player_id: str,
        player_name: str,
        position: str,
        college: str,
        draft_date: date
    ):
        """
        Execute draft pick with automatic transaction logging.

        Args:
            team_id: Team making selection
            round_number: Draft round
            pick_number: Overall pick number
            player_id: Player being selected
            player_name: Player's name
            position: Player's position
            college: Player's college
            draft_date: Date of draft

        Returns:
            EventResult from draft execution
        """
        print(f"\n{'=' * 60}")
        print(f"EXECUTING DRAFT PICK")
        print(f"{'=' * 60}")
        print(f"Team: {team_id}")
        print(f"Pick #{pick_number} (Round {round_number})")
        print(f"Player: {player_name} ({position}, {college})")
        print(f"Dynasty: {self.dynasty_id}")

        # Create event with transaction logger injected
        event = DraftPickEvent(
            team_id=team_id,
            round_number=round_number,
            pick_number=pick_number,
            player_id=player_id,
            player_name=player_name,
            position=position,
            college=college,
            event_date=Date.from_python_date(draft_date),
            dynasty_id=self.dynasty_id,
            transaction_logger=self.transaction_logger  # INJECT LOGGER
        )

        # Execute event (transaction logging happens automatically)
        result = event.simulate()

        if result.success:
            print(f"\nSUCCESS: {result.data.get('message')}")
            print(f"Transaction logged automatically")
        else:
            print(f"\nFAILED: {result.error_message}")

        return result

    def execute_player_release(
        self,
        team_id: int,
        player_id: str,
        contract_id: int,
        release_type: str,
        cap_savings: int,
        dead_cap: int,
        release_date: date
    ):
        """
        Execute player release with automatic transaction logging.

        Args:
            team_id: Team releasing the player
            player_id: Player being released
            contract_id: Contract being terminated
            release_type: PRE_JUNE_1 or POST_JUNE_1
            cap_savings: Cap space saved
            dead_cap: Dead cap hit
            release_date: Date of release

        Returns:
            EventResult from release execution
        """
        print(f"\n{'=' * 60}")
        print(f"EXECUTING PLAYER RELEASE")
        print(f"{'=' * 60}")
        print(f"Team: {team_id}")
        print(f"Player: {player_id}")
        print(f"Release Type: {release_type}")
        print(f"Dynasty: {self.dynasty_id}")

        # Create event with transaction logger injected
        event = PlayerReleaseEvent(
            team_id=team_id,
            player_id=player_id,
            contract_id=contract_id,
            release_type=release_type,
            cap_savings=cap_savings,
            dead_cap=dead_cap,
            event_date=Date.from_python_date(release_date),
            dynasty_id=self.dynasty_id,
            database_path=self.database_path,
            transaction_logger=self.transaction_logger  # INJECT LOGGER
        )

        # Execute event (transaction logging happens automatically if successful)
        result = event.simulate()

        if result.success:
            print(f"\nSUCCESS: {result.data.get('message')}")
            print(f"Dead Money: ${result.data.get('dead_money'):,}")
            print(f"Cap Savings: ${result.data.get('cap_savings'):,}")
            print(f"Transaction logged automatically")
        else:
            print(f"\nFAILED: {result.error_message}")

        return result

    def view_player_transaction_history(self, player_id: str):
        """
        View all transactions for a specific player.

        Args:
            player_id: Player to query

        Returns:
            List of transaction records
        """
        print(f"\n{'=' * 60}")
        print(f"PLAYER TRANSACTION HISTORY: {player_id}")
        print(f"{'=' * 60}")

        transactions = self.transaction_logger.get_player_transactions(
            player_id=player_id,
            dynasty_id=self.dynasty_id
        )

        if not transactions:
            print("No transactions found")
            return []

        for i, tx in enumerate(transactions, 1):
            print(f"\n{i}. {tx['transaction_type']} - {tx['transaction_date']}")
            print(f"   Player: {tx['player_name']} ({tx['position'] or 'N/A'})")
            print(f"   From Team: {tx['from_team_id'] or 'N/A'} ’ To Team: {tx['to_team_id'] or 'N/A'}")
            if tx['contract_id']:
                print(f"   Contract ID: {tx['contract_id']}")
            if tx['event_id']:
                print(f"   Event ID: {tx['event_id']}")

            # Display details if present
            if tx['details']:
                import json
                details = json.loads(tx['details'])
                print(f"   Details: {details}")

        return transactions

    def view_team_transaction_history(self, team_id: int, transaction_type: str = None):
        """
        View all transactions for a specific team.

        Args:
            team_id: Team to query
            transaction_type: Optional filter by transaction type

        Returns:
            List of transaction records
        """
        print(f"\n{'=' * 60}")
        print(f"TEAM TRANSACTION HISTORY: Team {team_id}")
        if transaction_type:
            print(f"Filter: {transaction_type}")
        print(f"{'=' * 60}")

        transactions = self.transaction_logger.get_team_transactions(
            team_id=team_id,
            dynasty_id=self.dynasty_id,
            season=self.season,
            transaction_type=transaction_type
        )

        if not transactions:
            print("No transactions found")
            return []

        for i, tx in enumerate(transactions, 1):
            print(f"\n{i}. {tx['transaction_type']} - {tx['transaction_date']}")
            print(f"   Player: {tx['player_name']} (ID: {tx['player_id']})")
            print(f"   From: {tx['from_team_id'] or 'N/A'} ’ To: {tx['to_team_id'] or 'N/A'}")

        print(f"\nTotal: {len(transactions)} transaction(s)")
        return transactions


def main():
    """
    Demonstration of transaction logging workflow integration.
    """
    print("=" * 60)
    print("TRANSACTION LOGGING WORKFLOW DEMONSTRATION")
    print("=" * 60)

    # Initialize workflow with transaction logging enabled
    workflow = OffseasonTransactionWorkflow(
        database_path=":memory:",  # Use in-memory database for demo
        dynasty_id="demo_dynasty",
        season=2025
    )

    print("\n" + "=" * 60)
    print("SCENARIO: Team rebuilds through offseason transactions")
    print("=" * 60)

    # 1. Sign a UFA (note: will fail cap validation without setup, but demonstrates pattern)
    print("\n\nSTEP 1: Free Agency Period")
    print("-" * 60)
    workflow.execute_free_agency_signing(
        team_id=7,  # Detroit Lions
        player_id="player_ufa_123",
        contract_years=3,
        contract_value=45_000_000,
        signing_bonus=15_000_000,
        base_salaries=[1_000_000, 14_000_000, 15_000_000],
        guaranteed_amounts=[1_000_000, 14_000_000, 0],
        signing_date=date(2025, 3, 15)
    )

    # 2. Draft a player
    print("\n\nSTEP 2: NFL Draft")
    print("-" * 60)
    workflow.execute_draft_pick(
        team_id=7,
        round_number=1,
        pick_number=15,
        player_id="player_draft_456",
        player_name="College Superstar",
        position="QB",
        college="Alabama",
        draft_date=date(2025, 4, 25)
    )

    # 3. Release a veteran (note: will fail without existing contract, but demonstrates pattern)
    print("\n\nSTEP 3: Roster Cuts")
    print("-" * 60)
    workflow.execute_player_release(
        team_id=7,
        player_id="player_vet_789",
        contract_id=999,  # Hypothetical contract
        release_type="POST_JUNE_1",
        cap_savings=10_000_000,
        dead_cap=5_000_000,
        release_date=date(2025, 6, 1)
    )

    # 4. View transaction history
    print("\n\nSTEP 4: Transaction History Review")
    print("-" * 60)
    workflow.view_team_transaction_history(team_id=7)

    # 5. View specific player history
    print("\n")
    workflow.view_player_transaction_history(player_id="player_draft_456")

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. TransactionLogger is optionally injected into events")
    print("2. Logging happens automatically after successful event execution")
    print("3. Events remain decoupled from logging (can work without logger)")
    print("4. Transaction history provides complete audit trail")
    print("5. Dynasty isolation ensures multi-save support")


if __name__ == "__main__":
    main()
