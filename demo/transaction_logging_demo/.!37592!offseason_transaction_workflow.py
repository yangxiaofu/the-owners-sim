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
from src.calendar.date_models import Date
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
