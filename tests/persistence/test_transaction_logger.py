"""
Unit tests for TransactionLogger.

Tests transaction logging functionality including:
- Direct log_transaction() method
- Event-based logging with log_from_event_result()
- Dynasty isolation
- Transaction data extraction and normalization
"""

import pytest
from datetime import date, datetime
from src.events.base_event import EventResult
from src.persistence.transaction_logger import TransactionLogger


class TestTransactionLoggerDirectLogging:
    """Test direct transaction logging via log_transaction() method."""

    def test_log_ufa_signing_transaction(self, test_db_with_schema):
        """Test logging UFA signing transaction directly."""
        logger = TransactionLogger(test_db_with_schema)

        tx_id = logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2025,
            transaction_type="UFA_SIGNING",
            player_id=12345,
            player_name="John Doe",
            transaction_date=date(2025, 3, 15),
            position="QB",
            from_team_id=None,  # UFA has no source team
            to_team_id=7,  # Detroit Lions
            details={
                "contract_years": 3,
                "contract_value": 45_000_000,
                "signing_bonus": 15_000_000,
                "avg_per_year": 15_000_000
            },
            contract_id=101,
            event_id="evt_ufa_001"
        )

        assert tx_id > 0

        # Verify transaction was logged
        transactions = logger.get_player_transactions(
            player_id=12345,
            dynasty_id="test_dynasty",
            season=2025
        )

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx["transaction_type"] == "UFA_SIGNING"
        assert tx["player_name"] == "John Doe"
        assert tx["to_team_id"] == 7
        assert tx["contract_id"] == 101

    def test_log_draft_pick_transaction(self, test_db_with_schema):
        """Test logging draft pick transaction directly."""
        logger = TransactionLogger(test_db_with_schema)

        tx_id = logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2025,
            transaction_type="DRAFT",
            player_id=67890,
            player_name="Jane Smith",
            transaction_date=date(2025, 4, 25),
            position="WR",
            from_team_id=None,  # Draft has no source team
            to_team_id=7,
            details={
                "round": 1,
                "pick": 15,
                "overall": 15,
                "college": "Alabama"
            },
            event_id="evt_draft_001"
        )

        assert tx_id > 0

        # Verify transaction was logged
        transactions = logger.get_player_transactions(
            player_id=67890,
            dynasty_id="test_dynasty"
        )

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx["transaction_type"] == "DRAFT"
        assert tx["player_name"] == "Jane Smith"
        assert tx["position"] == "WR"

    def test_log_player_release_transaction(self, test_db_with_schema):
        """Test logging player release transaction directly."""
        logger = TransactionLogger(test_db_with_schema)

        tx_id = logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2025,
            transaction_type="RELEASE",
            player_id=55555,
            player_name="Bob Johnson",
            transaction_date=date(2025, 6, 1),
            position="DE",
            from_team_id=7,
            to_team_id=None,  # Release has no destination team
            details={
                "release_type": "POST_JUNE_1",
                "dead_money": 5_000_000,
                "cap_savings": 8_000_000,
                "june_1_designation": True
            },
            contract_id=202
        )

        assert tx_id > 0

        # Verify transaction was logged
        transactions = logger.get_player_transactions(
            player_id=55555,
            dynasty_id="test_dynasty"
        )

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx["transaction_type"] == "RELEASE"
        assert tx["from_team_id"] == 7
        assert tx["to_team_id"] is None

    def test_invalid_transaction_type_raises_error(self, test_db_with_schema):
        """Test that invalid transaction type raises ValueError."""
        logger = TransactionLogger(test_db_with_schema)

        with pytest.raises(ValueError, match="Invalid transaction_type"):
            logger.log_transaction(
                dynasty_id="test_dynasty",
                season=2025,
                transaction_type="INVALID_TYPE",
                player_id=99999,
                player_name="Test Player",
                transaction_date=date(2025, 3, 1)
            )

    def test_required_parameters_validation(self, test_db_with_schema):
        """Test that required parameters are validated."""
        logger = TransactionLogger(test_db_with_schema)

        # Missing dynasty_id
        with pytest.raises(ValueError, match="dynasty_id is required"):
            logger.log_transaction(
                dynasty_id="",
                season=2025,
                transaction_type="DRAFT",
                player_id=12345,
                player_name="Test",
                transaction_date=date(2025, 4, 25)
            )

        # Missing player_id
        with pytest.raises(ValueError, match="player_id is required"):
            logger.log_transaction(
                dynasty_id="test_dynasty",
                season=2025,
                transaction_type="DRAFT",
                player_id=None,
                player_name="Test",
                transaction_date=date(2025, 4, 25)
            )


class TestTransactionLoggerEventIntegration:
    """Test event-based transaction logging via log_from_event_result()."""

    def test_log_from_ufa_signing_event_result(self, test_db_with_schema):
        """Test logging transaction from UFASigningEvent result."""
        logger = TransactionLogger(test_db_with_schema)

        # Create mock EventResult from UFA signing
        event_result = EventResult(
            event_id="evt_ufa_002",
            event_type="UFA_SIGNING",
            success=True,
            timestamp=datetime.now(),
            data={
                "player_id": "player_123",
                "team_id": 7,
                "contract_years": 4,
                "contract_value": 60_000_000,
                "signing_bonus": 20_000_000,
                "avg_per_year": 15_000_000,
                "contract_id": 303,
                "event_date": "2025-03-15",
                "dynasty_id": "test_dynasty"
            }
        )

        tx_id = logger.log_from_event_result(
            event_result=event_result,
            dynasty_id="test_dynasty",
            season=2025
        )

        assert tx_id > 0

        # Verify transaction was logged correctly
        transactions = logger.get_player_transactions(
            player_id="player_123",
            dynasty_id="test_dynasty"
        )

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx["transaction_type"] == "UFA_SIGNING"
        assert tx["to_team_id"] == 7
        assert tx["contract_id"] == 303
        assert tx["event_id"] == "evt_ufa_002"

    def test_log_from_draft_pick_event_result(self, test_db_with_schema):
        """Test logging transaction from DraftPickEvent result."""
        logger = TransactionLogger(test_db_with_schema)

        # Create mock EventResult from draft pick
        event_result = EventResult(
            event_id="evt_draft_002",
            event_type="DRAFT_PICK",
            success=True,
            timestamp=datetime.now(),
            data={
                "player_id": "player_456",
                "player_name": "College Star",
                "position": "RB",
                "team_id": 7,
                "round_number": 2,
                "pick_number": 47,
                "college": "Ohio State",
                "event_date": "2025-04-26",
                "dynasty_id": "test_dynasty"
            }
        )

        tx_id = logger.log_from_event_result(
            event_result=event_result,
            dynasty_id="test_dynasty",
            season=2025
        )

        assert tx_id > 0

        # Verify transaction was logged correctly
        transactions = logger.get_player_transactions(
            player_id="player_456",
            dynasty_id="test_dynasty"
        )

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx["transaction_type"] == "DRAFT"
        assert tx["player_name"] == "College Star"
        assert tx["position"] == "RB"
        assert tx["to_team_id"] == 7

        # Verify details JSON
        import json
        details = json.loads(tx["details"])
        assert details["round"] == 2
        assert details["pick"] == 47
        assert details["college"] == "Ohio State"

    def test_log_from_player_release_event_result(self, test_db_with_schema):
        """Test logging transaction from PlayerReleaseEvent result."""
        logger = TransactionLogger(test_db_with_schema)

        # Create mock EventResult from player release
        event_result = EventResult(
            event_id="evt_release_001",
            event_type="PLAYER_RELEASE",
            success=True,
            timestamp=datetime.now(),
            data={
                "player_id": "player_789",
                "team_id": 7,
                "contract_id": 404,
                "release_type": "PRE_JUNE_1",
                "dead_money": 3_000_000,
                "cap_savings": 10_000_000,
                "june_1_designation": False,
                "event_date": "2025-03-10",
                "dynasty_id": "test_dynasty"
            }
        )

        tx_id = logger.log_from_event_result(
            event_result=event_result,
            dynasty_id="test_dynasty",
            season=2025
        )

        assert tx_id > 0

        # Verify transaction was logged correctly
        transactions = logger.get_player_transactions(
            player_id="player_789",
            dynasty_id="test_dynasty"
        )

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx["transaction_type"] == "RELEASE"
        assert tx["from_team_id"] == 7
        assert tx["to_team_id"] is None
        assert tx["contract_id"] == 404

        # Verify details JSON
        import json
        details = json.loads(tx["details"])
        assert details["release_type"] == "PRE_JUNE_1"
        assert details["dead_money"] == 3_000_000
        assert details["cap_savings"] == 10_000_000

    def test_unsupported_event_type_raises_error(self, test_db_with_schema):
        """Test that unsupported event types raise ValueError."""
        logger = TransactionLogger(test_db_with_schema)

        # Create mock EventResult with unsupported type
        event_result = EventResult(
            event_id="evt_unsupported",
            event_type="GAME_SIMULATION",
            success=True,
            timestamp=datetime.now(),
            data={}
        )

        with pytest.raises(ValueError, match="Unsupported event type"):
            logger.log_from_event_result(
                event_result=event_result,
                dynasty_id="test_dynasty",
                season=2025
            )


class TestTransactionLoggerDynastyIsolation:
    """Test dynasty isolation for transaction logging."""

    def test_same_player_different_dynasties(self, test_db_with_schema):
        """Test that same player_id in different dynasties are isolated."""
        logger = TransactionLogger(test_db_with_schema)

        player_id = 11111

        # Log transaction in dynasty 1
        logger.log_transaction(
            dynasty_id="dynasty_1",
            season=2025,
            transaction_type="UFA_SIGNING",
            player_id=player_id,
            player_name="Multi Dynasty Player",
            transaction_date=date(2025, 3, 15),
            to_team_id=7
        )

        # Log transaction in dynasty 2
        logger.log_transaction(
            dynasty_id="dynasty_2",
            season=2025,
            transaction_type="DRAFT",
            player_id=player_id,
            player_name="Multi Dynasty Player",
            transaction_date=date(2025, 4, 25),
            to_team_id=9
        )

        # Verify each dynasty sees only its own transaction
        dynasty1_txs = logger.get_player_transactions(
            player_id=player_id,
            dynasty_id="dynasty_1"
        )
        assert len(dynasty1_txs) == 1
        assert dynasty1_txs[0]["transaction_type"] == "UFA_SIGNING"

        dynasty2_txs = logger.get_player_transactions(
            player_id=player_id,
            dynasty_id="dynasty_2"
        )
        assert len(dynasty2_txs) == 1
        assert dynasty2_txs[0]["transaction_type"] == "DRAFT"

    def test_team_transactions_dynasty_isolation(self, test_db_with_schema):
        """Test team transaction queries respect dynasty isolation."""
        logger = TransactionLogger(test_db_with_schema)

        team_id = 7

        # Log transactions in different dynasties for same team
        logger.log_transaction(
            dynasty_id="dynasty_alpha",
            season=2025,
            transaction_type="UFA_SIGNING",
            player_id=22222,
            player_name="Player A",
            transaction_date=date(2025, 3, 15),
            to_team_id=team_id
        )

        logger.log_transaction(
            dynasty_id="dynasty_beta",
            season=2025,
            transaction_type="DRAFT",
            player_id=33333,
            player_name="Player B",
            transaction_date=date(2025, 4, 25),
            to_team_id=team_id
        )

        # Verify each dynasty sees only its own team transactions
        alpha_txs = logger.get_team_transactions(
            team_id=team_id,
            dynasty_id="dynasty_alpha"
        )
        assert len(alpha_txs) == 1
        assert alpha_txs[0]["player_id"] == 22222

        beta_txs = logger.get_team_transactions(
            team_id=team_id,
            dynasty_id="dynasty_beta"
        )
        assert len(beta_txs) == 1
        assert beta_txs[0]["player_id"] == 33333


class TestTransactionLoggerQueryMethods:
    """Test transaction query methods."""

    def test_get_player_transactions_with_season_filter(self, test_db_with_schema):
        """Test querying player transactions with season filter."""
        logger = TransactionLogger(test_db_with_schema)

        player_id = 44444

        # Log transactions in different seasons
        logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2024,
            transaction_type="DRAFT",
            player_id=player_id,
            player_name="Rookie",
            transaction_date=date(2024, 4, 25),
            to_team_id=7
        )

        logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2025,
            transaction_type="RESTRUCTURE",
            player_id=player_id,
            player_name="Rookie",
            transaction_date=date(2025, 3, 10),
            to_team_id=7
        )

        # Query with season filter
        txs_2024 = logger.get_player_transactions(
            player_id=player_id,
            dynasty_id="test_dynasty",
            season=2024
        )
        assert len(txs_2024) == 1
        assert txs_2024[0]["season"] == 2024

        txs_2025 = logger.get_player_transactions(
            player_id=player_id,
            dynasty_id="test_dynasty",
            season=2025
        )
        assert len(txs_2025) == 1
        assert txs_2025[0]["season"] == 2025

    def test_get_team_transactions_with_type_filter(self, test_db_with_schema):
        """Test querying team transactions with type filter."""
        logger = TransactionLogger(test_db_with_schema)

        team_id = 7

        # Log different transaction types for same team
        logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2025,
            transaction_type="UFA_SIGNING",
            player_id=55555,
            player_name="FA Player",
            transaction_date=date(2025, 3, 15),
            to_team_id=team_id
        )

        logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2025,
            transaction_type="DRAFT",
            player_id=66666,
            player_name="Draft Pick",
            transaction_date=date(2025, 4, 25),
            to_team_id=team_id
        )

        logger.log_transaction(
            dynasty_id="test_dynasty",
            season=2025,
            transaction_type="RELEASE",
            player_id=77777,
            player_name="Released Player",
            transaction_date=date(2025, 6, 1),
            from_team_id=team_id
        )

        # Query with type filter
        ufa_txs = logger.get_team_transactions(
            team_id=team_id,
            dynasty_id="test_dynasty",
            transaction_type="UFA_SIGNING"
        )
        assert len(ufa_txs) == 1
        assert ufa_txs[0]["transaction_type"] == "UFA_SIGNING"

        draft_txs = logger.get_team_transactions(
            team_id=team_id,
            dynasty_id="test_dynasty",
            transaction_type="DRAFT"
        )
        assert len(draft_txs) == 1
        assert draft_txs[0]["transaction_type"] == "DRAFT"

    def test_transaction_data_extraction_and_normalization(self, test_db_with_schema):
        """Test that transaction data is correctly extracted and normalized."""
        logger = TransactionLogger(test_db_with_schema)

        # Test franchise tag event (has unique fields)
        event_result = EventResult(
            event_id="evt_tag_001",
            event_type="FRANCHISE_TAG",
            success=True,
            timestamp=datetime.now(),
            data={
                "player_id": "player_tag",
                "team_id": 7,
                "player_position": "QB",
                "tag_type": "FRANCHISE_EXCLUSIVE",
                "tag_salary": 35_000_000,
                "cap_impact": 35_000_000,
                "contract_id": 505,
                "event_date": "2025-02-20",
                "dynasty_id": "test_dynasty"
            }
        )

        tx_id = logger.log_from_event_result(
            event_result=event_result,
            dynasty_id="test_dynasty",
            season=2025
        )

        # Verify normalization
        transactions = logger.get_player_transactions(
            player_id="player_tag",
            dynasty_id="test_dynasty"
        )

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx["transaction_type"] == "FRANCHISE_TAG"
        assert tx["position"] == "QB"

        # Verify details were normalized correctly
        import json
        details = json.loads(tx["details"])
        assert details["tag_type"] == "FRANCHISE_EXCLUSIVE"
        assert details["tag_salary"] == 35_000_000
