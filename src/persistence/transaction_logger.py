"""
Transaction Logger

Service for persisting player transactions to the database.
Provides methods for logging all types of NFL roster moves, contract actions,
and personnel changes with dynasty isolation.

Integrates with the event system to extract transaction data from EventResult
objects and normalize them for database storage.
"""

import json
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import date

from database.connection import DatabaseConnection

if TYPE_CHECKING:
    from events.base_event import EventResult


class TransactionLogger:
    """
    Service for logging player transactions to the database.

    Supports all NFL transaction types including:
    - Draft picks and UDFA signings
    - Free agency signings (UFA, RFA)
    - Roster cuts and releases
    - Franchise tags and transition tags
    - Waiver claims and practice squad moves
    - Contract restructures

    Features:
    - Dynasty isolation for multi-save support
    - Event system integration for automated logging
    - JSON storage for transaction-specific details
    - Contract and event ID linking
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Transaction Logger.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.db_connection = DatabaseConnection(database_path)
        self.logger = logging.getLogger(__name__)

    def log_transaction(
        self,
        dynasty_id: str,
        season: int,
        transaction_type: str,
        player_id: int,
        player_name: str,
        transaction_date: date,
        position: Optional[str] = None,
        from_team_id: Optional[int] = None,
        to_team_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        contract_id: Optional[int] = None,
        event_id: Optional[str] = None
    ) -> int:
        """
        Log a player transaction directly to the database.

        This method provides complete control over all transaction fields.
        Use log_from_event_result() for automated logging from events.

        Args:
            dynasty_id: Dynasty identifier for isolation (REQUIRED)
            season: Season year
            transaction_type: Type of transaction (DRAFT, UFA_SIGNING, etc.)
            player_id: Player ID
            player_name: Player's full name (will be split into first/last)
            transaction_date: Date of transaction
            position: Player's position (optional)
            from_team_id: Originating team (NULL for draft/UDFA)
            to_team_id: Destination team (NULL for releases/cuts)
            details: Transaction-specific data as dict (will be JSON-encoded)
            contract_id: Associated contract ID (optional)
            event_id: Associated event ID (optional)

        Returns:
            transaction_id of newly created transaction

        Raises:
            ValueError: If required parameters are missing or invalid
            sqlite3.Error: If database operation fails

        Example:
            >>> logger = TransactionLogger()
            >>> tx_id = logger.log_transaction(
            ...     dynasty_id="my_dynasty",
            ...     season=2024,
            ...     transaction_type="DRAFT",
            ...     player_id=12345,
            ...     player_name="John Doe",
            ...     transaction_date=date(2024, 4, 25),
            ...     position="QB",
            ...     to_team_id=7,
            ...     details={"round": 1, "pick": 15, "overall": 15}
            ... )
        """
        # Validate required parameters
        if not dynasty_id:
            raise ValueError("dynasty_id is required for transaction logging")
        if not transaction_type:
            raise ValueError("transaction_type is required")
        if not player_id:
            raise ValueError("player_id is required")
        if not player_name:
            raise ValueError("player_name is required")
        if not transaction_date:
            raise ValueError("transaction_date is required")

        # Split player_name into first_name and last_name
        name_parts = player_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Validate transaction type
        valid_types = [
            'DRAFT', 'UDFA_SIGNING', 'UFA_SIGNING', 'RFA_SIGNING',
            'RELEASE', 'WAIVER_CLAIM', 'TRADE', 'ROSTER_CUT',
            'PRACTICE_SQUAD_ADD', 'PRACTICE_SQUAD_REMOVE',
            'PRACTICE_SQUAD_ELEVATE', 'FRANCHISE_TAG',
            'TRANSITION_TAG', 'RESTRUCTURE'
        ]
        if transaction_type not in valid_types:
            raise ValueError(f"Invalid transaction_type: {transaction_type}. Must be one of {valid_types}")

        # Convert details dict to JSON string if provided
        details_json = json.dumps(details) if details else None

        # Insert transaction
        return self._insert_transaction(
            dynasty_id=dynasty_id,
            season=season,
            transaction_type=transaction_type,
            player_id=player_id,
            first_name=first_name,
            last_name=last_name,
            position=position,
            from_team_id=from_team_id,
            to_team_id=to_team_id,
            transaction_date=transaction_date,
            details_json=details_json,
            contract_id=contract_id,
            event_id=event_id
        )

    def log_from_event_result(
        self,
        event_result: "EventResult",
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Extract transaction data from EventResult and log to database.

        Automatically normalizes different event types into transaction records.
        Supports:
        - DRAFT_PICK -> DRAFT
        - UFA_SIGNING -> UFA_SIGNING
        - ROSTER_CUT -> ROSTER_CUT
        - FRANCHISE_TAG -> FRANCHISE_TAG
        - TRANSITION_TAG -> TRANSITION_TAG
        - PLAYER_RELEASE -> RELEASE
        - WAIVER_CLAIM -> WAIVER_CLAIM
        - RFA_OFFER_SHEET -> RFA_SIGNING

        Args:
            event_result: EventResult from event simulation
            dynasty_id: Dynasty identifier for isolation
            season: Season year

        Returns:
            transaction_id of newly created transaction

        Raises:
            ValueError: If event type is not supported or required data is missing
            KeyError: If expected data fields are missing from event_result

        Example:
            >>> logger = TransactionLogger()
            >>> event_result = draft_pick_event.simulate()
            >>> tx_id = logger.log_from_event_result(
            ...     event_result=event_result,
            ...     dynasty_id="my_dynasty",
            ...     season=2024
            ... )
        """
        # Extract and normalize transaction data
        tx_data = self._normalize_event_result(event_result)

        # Add dynasty and season
        tx_data['dynasty_id'] = dynasty_id
        tx_data['season'] = season

        # Log the transaction
        return self.log_transaction(**tx_data)

    def _normalize_event_result(self, event_result: "EventResult") -> Dict[str, Any]:
        """
        Extract transaction data from EventResult based on event type.

        Maps event-specific data structures to the standardized transaction format.

        Args:
            event_result: EventResult from event simulation

        Returns:
            Dictionary with normalized transaction data ready for log_transaction()

        Raises:
            ValueError: If event type is not supported or required data is missing
            KeyError: If expected data fields are missing from event_result.data
        """
        event_type = event_result.event_type
        data = event_result.data

        # Map event type to transaction type and extract fields
        if event_type == "DRAFT_PICK":
            return {
                "transaction_type": "DRAFT",
                "player_id": data["player_id"],
                "player_name": data["player_name"],
                "position": data.get("position"),
                "from_team_id": None,
                "to_team_id": data["team_id"],
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "round": data["round_number"],
                    "pick": data["pick_number"],
                    "overall": data["pick_number"],
                    "college": data.get("college")
                },
                "contract_id": None,
                "event_id": event_result.event_id
            }

        elif event_type == "UFA_SIGNING":
            return {
                "transaction_type": "UFA_SIGNING",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": None,  # Not typically in UFA event data
                "from_team_id": None,  # UFA = unrestricted
                "to_team_id": data["team_id"],
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "contract_years": data.get("contract_years"),
                    "contract_value": data.get("contract_value"),
                    "signing_bonus": data.get("signing_bonus"),
                    "avg_per_year": data.get("avg_per_year")
                },
                "contract_id": data.get("contract_id"),
                "event_id": event_result.event_id
            }

        elif event_type == "RFA_OFFER_SHEET":
            # RFA offer sheet becomes RFA_SIGNING transaction
            return {
                "transaction_type": "RFA_SIGNING",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": None,
                "from_team_id": data.get("original_team_id") if not data.get("matched") else None,
                "to_team_id": data.get("final_team_id", data.get("signing_team_id")),
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "offer_amount": data.get("offer_amount"),
                    "contract_years": data.get("contract_years"),
                    "tender_level": data.get("tender_level"),
                    "matched": data.get("matched"),
                    "original_team_id": data.get("original_team_id"),
                    "signing_team_id": data.get("signing_team_id")
                },
                "contract_id": data.get("contract_id"),
                "event_id": event_result.event_id
            }

        elif event_type == "ROSTER_CUT":
            return {
                "transaction_type": "ROSTER_CUT",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": None,
                "from_team_id": data["team_id"],
                "to_team_id": None,
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "cut_type": data.get("cut_type"),
                    "reason": data.get("reason")
                },
                "contract_id": None,
                "event_id": event_result.event_id
            }

        elif event_type == "FRANCHISE_TAG":
            return {
                "transaction_type": "FRANCHISE_TAG",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": data.get("player_position"),
                "from_team_id": None,
                "to_team_id": data["team_id"],
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "tag_type": data.get("tag_type"),
                    "tag_salary": data.get("tag_salary"),
                    "cap_impact": data.get("cap_impact")
                },
                "contract_id": data.get("contract_id"),
                "event_id": event_result.event_id
            }

        elif event_type == "TRANSITION_TAG":
            return {
                "transaction_type": "TRANSITION_TAG",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": data.get("player_position"),
                "from_team_id": None,
                "to_team_id": data["team_id"],
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "tag_salary": data.get("tag_salary"),
                    "cap_impact": data.get("cap_impact")
                },
                "contract_id": data.get("contract_id"),
                "event_id": event_result.event_id
            }

        elif event_type == "PLAYER_RELEASE":
            return {
                "transaction_type": "RELEASE",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": None,
                "from_team_id": data["team_id"],
                "to_team_id": None,
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "release_type": data.get("release_type"),
                    "dead_money": data.get("dead_money"),
                    "cap_savings": data.get("cap_savings"),
                    "june_1_designation": data.get("june_1_designation")
                },
                "contract_id": data.get("contract_id"),
                "event_id": event_result.event_id
            }

        elif event_type == "WAIVER_CLAIM":
            return {
                "transaction_type": "WAIVER_CLAIM",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": None,
                "from_team_id": data.get("releasing_team_id"),
                "to_team_id": data.get("claiming_team_id") if data.get("claim_successful") else None,
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "waiver_priority": data.get("waiver_priority"),
                    "claim_successful": data.get("claim_successful")
                },
                "contract_id": None,
                "event_id": event_result.event_id
            }

        elif event_type == "CONTRACT_RESTRUCTURE":
            return {
                "transaction_type": "RESTRUCTURE",
                "player_id": data["player_id"],
                "player_name": data.get("player_name", f"Player {data['player_id']}"),
                "position": None,
                "from_team_id": None,
                "to_team_id": data["team_id"],
                "transaction_date": date.fromisoformat(data["event_date"]),
                "details": {
                    "year_to_restructure": data.get("year_to_restructure"),
                    "restructure_amount": data.get("restructure_amount"),
                    "cap_savings": data.get("cap_savings"),
                    "dead_money_increase": data.get("dead_money_increase")
                },
                "contract_id": data.get("contract_id"),
                "event_id": event_result.event_id
            }

        else:
            raise ValueError(
                f"Unsupported event type for transaction logging: {event_type}. "
                f"Supported types: DRAFT_PICK, UFA_SIGNING, RFA_OFFER_SHEET, ROSTER_CUT, "
                f"FRANCHISE_TAG, TRANSITION_TAG, PLAYER_RELEASE, WAIVER_CLAIM, CONTRACT_RESTRUCTURE"
            )

    def _insert_transaction(
        self,
        dynasty_id: str,
        season: int,
        transaction_type: str,
        player_id: int,
        first_name: str,
        last_name: str,
        transaction_date: date,
        position: Optional[str] = None,
        from_team_id: Optional[int] = None,
        to_team_id: Optional[int] = None,
        details_json: Optional[str] = None,
        contract_id: Optional[int] = None,
        event_id: Optional[str] = None
    ) -> int:
        """
        Insert transaction record into database.

        Private method for database insertion - use log_transaction() or
        log_from_event_result() instead.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            transaction_type: Type of transaction
            player_id: Player ID
            first_name: Player's first name
            last_name: Player's last name
            transaction_date: Date of transaction
            position: Player's position (optional)
            from_team_id: Originating team (optional)
            to_team_id: Destination team (optional)
            details_json: JSON-encoded details string (optional)
            contract_id: Associated contract ID (optional)
            event_id: Associated event ID (optional)

        Returns:
            transaction_id of newly created transaction

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self.db_connection.get_connection()

        try:
            cursor = conn.execute('''
                INSERT INTO player_transactions (
                    dynasty_id, season, transaction_type,
                    player_id, first_name, last_name, position,
                    from_team_id, to_team_id,
                    transaction_date, details,
                    contract_id, event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dynasty_id, season, transaction_type,
                player_id, first_name, last_name, position,
                from_team_id, to_team_id,
                transaction_date, details_json,
                contract_id, event_id
            ))

            conn.commit()
            transaction_id = cursor.lastrowid

            player_name = f"{first_name} {last_name}".strip()
            self.logger.info(
                f"Logged {transaction_type} transaction for player {player_name} "
                f"(ID: {player_id}) in dynasty {dynasty_id}, season {season} "
                f"[transaction_id: {transaction_id}]"
            )

            return transaction_id

        except Exception as e:
            conn.rollback()
            player_name = f"{first_name} {last_name}".strip()
            self.logger.error(
                f"Error inserting transaction: {e} "
                f"[dynasty: {dynasty_id}, season: {season}, type: {transaction_type}, "
                f"player: {player_name}]"
            )
            raise
        finally:
            conn.close()
