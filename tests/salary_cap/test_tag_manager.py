"""
Unit tests for TagManager

Tests franchise tags, transition tags, and RFA tenders including:
- Franchise tag salary calculations (top 5 average)
- Transition tag salary calculations (top 10 average)
- Consecutive tag escalators (120%, 144%)
- RFA tender calculations (4 levels)
- Tag application and database persistence
- Tag history tracking
"""

import pytest
from datetime import date

from salary_cap import TagManager, CapDatabaseAPI, ContractManager


class TestFranchiseTagCalculations:
    """Test franchise tag salary calculations."""

    def test_calculate_franchise_tag_salary_no_data(self, test_db_path):
        """Test franchise tag calculation with no historical data."""
        tag_mgr = TagManager(test_db_path)

        # Should return default minimum when no data exists
        tag_salary = tag_mgr.calculate_franchise_tag_salary(
            position="QB",
            season=2025,
            dynasty_id="test_dynasty",
            tag_type="NON_EXCLUSIVE"
        )

        # Should return a reasonable default
        assert tag_salary == 10_000_000

    def test_calculate_franchise_tag_exclusive_vs_non_exclusive(self, test_db_path):
        """Test that exclusive and non-exclusive tags use same calculation."""
        tag_mgr = TagManager(test_db_path)

        exclusive_tag = tag_mgr.calculate_franchise_tag_salary(
            position="QB",
            season=2025,
            dynasty_id="test_dynasty",
            tag_type="EXCLUSIVE"
        )

        non_exclusive_tag = tag_mgr.calculate_franchise_tag_salary(
            position="QB",
            season=2025,
            dynasty_id="test_dynasty",
            tag_type="NON_EXCLUSIVE"
        )

        # Both should return same value (calculation is identical)
        assert exclusive_tag == non_exclusive_tag


class TestTransitionTagCalculations:
    """Test transition tag salary calculations."""

    def test_calculate_transition_tag_salary_no_data(self, test_db_path):
        """Test transition tag calculation with no historical data."""
        tag_mgr = TagManager(test_db_path)

        # Should return default minimum when no data exists
        tag_salary = tag_mgr.calculate_transition_tag_salary(
            position="WR",
            season=2025,
            dynasty_id="test_dynasty"
        )

        # Should return a reasonable default (lower than franchise tag)
        assert tag_salary == 8_000_000


class TestConsecutiveTagEscalators:
    """Test consecutive franchise tag escalators."""

    def test_apply_first_franchise_tag(self, test_db_path):
        """Test applying first franchise tag to player."""
        tag_mgr = TagManager(test_db_path)

        # Apply first franchise tag
        tag_salary = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            position="QB",
            tag_type="NON_EXCLUSIVE",
            tag_date=date(2025, 3, 1)
        )

        # Should use calculated salary (default: 10M)
        assert tag_salary == 10_000_000

        # Verify tag was stored in database
        db_api = CapDatabaseAPI(test_db_path)
        tags = db_api.get_team_franchise_tags(1, 2025, "test_dynasty")
        assert len(tags) == 1
        assert tags[0]['tag_type'] == "FRANCHISE_NON_EXCLUSIVE"
        assert tags[0]['tag_salary'] == 10_000_000
        assert tags[0]['consecutive_tag_number'] == 1

    def test_apply_second_consecutive_franchise_tag(self, test_db_path):
        """Test 120% escalator for second consecutive tag."""
        tag_mgr = TagManager(test_db_path)

        # Apply first tag in 2024
        first_tag_salary = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2024,
            dynasty_id="test_dynasty",
            position="QB",
            tag_type="NON_EXCLUSIVE"
        )
        assert first_tag_salary == 10_000_000  # Base default

        # Apply second consecutive tag in 2025
        second_tag_salary = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            position="QB",
            tag_type="NON_EXCLUSIVE"
        )

        # Should be 120% of first tag
        expected_second_tag = int(first_tag_salary * 1.20)
        assert second_tag_salary == expected_second_tag
        assert second_tag_salary == 12_000_000  # 120% of 10M

        # Verify consecutive tag number
        db_api = CapDatabaseAPI(test_db_path)
        tags = db_api.get_team_franchise_tags(1, 2025, "test_dynasty")
        assert len(tags) == 1
        assert tags[0]['consecutive_tag_number'] == 2

    def test_apply_third_consecutive_franchise_tag(self, test_db_path):
        """Test 144% escalator for third consecutive tag."""
        tag_mgr = TagManager(test_db_path)

        # Apply first tag
        first_tag_salary = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2024,
            dynasty_id="test_dynasty",
            position="QB",
            tag_type="NON_EXCLUSIVE"
        )
        assert first_tag_salary == 10_000_000

        # Apply second tag
        second_tag_salary = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            position="QB",
            tag_type="NON_EXCLUSIVE"
        )
        assert second_tag_salary == 12_000_000

        # Apply third consecutive tag
        third_tag_salary = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2026,
            dynasty_id="test_dynasty",
            position="QB",
            tag_type="NON_EXCLUSIVE"
        )

        # Should be 144% of FIRST tag (not second)
        expected_third_tag = int(first_tag_salary * 1.44)
        assert third_tag_salary == expected_third_tag
        assert third_tag_salary == 14_400_000  # 144% of 10M

        # Verify consecutive tag number
        db_api = CapDatabaseAPI(test_db_path)
        tags = db_api.get_team_franchise_tags(1, 2026, "test_dynasty")
        assert len(tags) == 1
        assert tags[0]['consecutive_tag_number'] == 3

    def test_consecutive_tags_different_teams_reset(self, test_db_path):
        """Test that tags with different teams don't count as consecutive."""
        tag_mgr = TagManager(test_db_path)

        # Tag player with Team 1
        tag1 = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2024,
            dynasty_id="test_dynasty",
            position="QB"
        )
        assert tag1 == 10_000_000

        # Tag same player with Team 2 (different team)
        tag2 = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=2,
            season=2025,
            dynasty_id="test_dynasty",
            position="QB"
        )

        # Should be treated as first tag (not second)
        assert tag2 == 10_000_000

        # Verify consecutive tag number is 1
        db_api = CapDatabaseAPI(test_db_path)
        tags = db_api.get_team_franchise_tags(2, 2025, "test_dynasty")
        assert tags[0]['consecutive_tag_number'] == 1


class TestTransitionTagApplication:
    """Test transition tag application."""

    def test_apply_transition_tag(self, test_db_path):
        """Test applying transition tag to player."""
        tag_mgr = TagManager(test_db_path)

        tag_salary = tag_mgr.apply_transition_tag(
            player_id=200,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            position="WR",
            tag_date=date(2025, 3, 1)
        )

        # Should use calculated salary (default: 8M)
        assert tag_salary == 8_000_000

        # Verify tag was stored
        db_api = CapDatabaseAPI(test_db_path)
        tags = db_api.get_team_franchise_tags(1, 2025, "test_dynasty")
        assert len(tags) == 1
        assert tags[0]['tag_type'] == "TRANSITION"
        assert tags[0]['tag_salary'] == 8_000_000
        assert tags[0]['consecutive_tag_number'] == 1  # No escalators

    def test_transition_tag_no_consecutive_escalators(self, test_db_path):
        """Test that transition tags don't have consecutive escalators."""
        tag_mgr = TagManager(test_db_path)

        # Apply transition tag in 2024
        tag1 = tag_mgr.apply_transition_tag(
            player_id=200,
            team_id=1,
            season=2024,
            dynasty_id="test_dynasty",
            position="WR"
        )
        assert tag1 == 8_000_000

        # Apply transition tag in 2025
        tag2 = tag_mgr.apply_transition_tag(
            player_id=200,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            position="WR"
        )

        # Should be same as first (no escalator)
        assert tag2 == 8_000_000


class TestRFATenderCalculations:
    """Test RFA tender calculations."""

    def test_calculate_first_round_tender(self, test_db_path):
        """Test first round RFA tender calculation."""
        tag_mgr = TagManager(test_db_path)

        tender_amount = tag_mgr.calculate_rfa_tender(
            tender_level="FIRST_ROUND",
            season=2025,
            player_previous_salary=0
        )

        # Should return first round tender base
        assert tender_amount == tag_mgr.RFA_FIRST_ROUND_TENDER
        assert tender_amount == 4_158_000

    def test_calculate_second_round_tender(self, test_db_path):
        """Test second round RFA tender calculation."""
        tag_mgr = TagManager(test_db_path)

        tender_amount = tag_mgr.calculate_rfa_tender(
            tender_level="SECOND_ROUND",
            season=2025,
            player_previous_salary=0
        )

        assert tender_amount == tag_mgr.RFA_SECOND_ROUND_TENDER
        assert tender_amount == 3_116_000

    def test_calculate_original_round_tender(self, test_db_path):
        """Test original round RFA tender calculation."""
        tag_mgr = TagManager(test_db_path)

        tender_amount = tag_mgr.calculate_rfa_tender(
            tender_level="ORIGINAL_ROUND",
            season=2025,
            player_previous_salary=0
        )

        assert tender_amount == tag_mgr.RFA_ORIGINAL_ROUND_TENDER
        assert tender_amount == 2_985_000

    def test_calculate_right_of_first_refusal_tender(self, test_db_path):
        """Test right of first refusal RFA tender calculation."""
        tag_mgr = TagManager(test_db_path)

        tender_amount = tag_mgr.calculate_rfa_tender(
            tender_level="RIGHT_OF_FIRST_REFUSAL",
            season=2025,
            player_previous_salary=0
        )

        assert tender_amount == tag_mgr.RFA_RIGHT_OF_FIRST_REFUSAL
        assert tender_amount == 2_985_000

    def test_calculate_tender_with_110_percent_escalator(self, test_db_path):
        """Test that tender uses higher of base OR 110% of previous salary."""
        tag_mgr = TagManager(test_db_path)

        # Player made $5M last year
        # 110% of $5M = $5.5M
        # First round tender base = $4.158M
        # Should use $5.5M (higher)
        tender_amount = tag_mgr.calculate_rfa_tender(
            tender_level="FIRST_ROUND",
            season=2025,
            player_previous_salary=5_000_000
        )

        expected_escalated = int(5_000_000 * 1.10)
        assert tender_amount == expected_escalated
        assert tender_amount == 5_500_000

    def test_calculate_tender_base_higher_than_escalated(self, test_db_path):
        """Test that tender uses base when it's higher than 110% escalator."""
        tag_mgr = TagManager(test_db_path)

        # Player made $1M last year
        # 110% of $1M = $1.1M
        # First round tender base = $4.158M
        # Should use $4.158M (higher)
        tender_amount = tag_mgr.calculate_rfa_tender(
            tender_level="FIRST_ROUND",
            season=2025,
            player_previous_salary=1_000_000
        )

        assert tender_amount == tag_mgr.RFA_FIRST_ROUND_TENDER
        assert tender_amount == 4_158_000

    def test_invalid_tender_level_raises_error(self, test_db_path):
        """Test that invalid tender level raises ValueError."""
        tag_mgr = TagManager(test_db_path)

        with pytest.raises(ValueError, match="Invalid tender level"):
            tag_mgr.calculate_rfa_tender(
                tender_level="INVALID_LEVEL",
                season=2025,
                player_previous_salary=0
            )


class TestRFATenderApplication:
    """Test RFA tender application."""

    def test_apply_first_round_rfa_tender(self, test_db_path):
        """Test applying first round RFA tender."""
        tag_mgr = TagManager(test_db_path)

        tender_salary = tag_mgr.apply_rfa_tender(
            player_id=300,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            tender_level="FIRST_ROUND",
            player_previous_salary=2_000_000,
            tender_date=date(2025, 4, 1)
        )

        # Should use first round base (higher than 110% of $2M)
        assert tender_salary == 4_158_000

        # Verify tender was stored
        db_api = CapDatabaseAPI(test_db_path)
        conn = db_api._get_connection()
        cursor = conn.execute(
            "SELECT * FROM rfa_tenders WHERE player_id = ? AND team_id = ? AND season = ?",
            (300, 1, 2025)
        )
        tender = cursor.fetchone()
        conn.close()

        assert tender is not None
        assert tender[5] == "FIRST_ROUND"  # tender_level
        assert tender[6] == 4_158_000  # tender_salary
        assert tender[8] == 1  # compensation_round

    def test_apply_second_round_rfa_tender(self, test_db_path):
        """Test applying second round RFA tender."""
        tag_mgr = TagManager(test_db_path)

        tender_salary = tag_mgr.apply_rfa_tender(
            player_id=301,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            tender_level="SECOND_ROUND",
            player_previous_salary=0
        )

        assert tender_salary == 3_116_000

        # Verify compensation round
        db_api = CapDatabaseAPI(test_db_path)
        conn = db_api._get_connection()
        cursor = conn.execute(
            "SELECT compensation_round FROM rfa_tenders WHERE player_id = ?",
            (301,)
        )
        result = cursor.fetchone()
        conn.close()

        assert result[0] == 2  # Second round compensation

    def test_apply_right_of_first_refusal_no_compensation(self, test_db_path):
        """Test that ROFR tender has no draft compensation."""
        tag_mgr = TagManager(test_db_path)

        tender_salary = tag_mgr.apply_rfa_tender(
            player_id=302,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            tender_level="RIGHT_OF_FIRST_REFUSAL",
            player_previous_salary=0
        )

        assert tender_salary == 2_985_000

        # Verify no compensation
        db_api = CapDatabaseAPI(test_db_path)
        conn = db_api._get_connection()
        cursor = conn.execute(
            "SELECT compensation_round FROM rfa_tenders WHERE player_id = ?",
            (302,)
        )
        result = cursor.fetchone()
        conn.close()

        assert result[0] is None  # No compensation


class TestContractCreation:
    """Test that tags create proper 1-year contracts."""

    def test_franchise_tag_creates_contract(self, test_db_path):
        """Test that applying franchise tag creates 1-year contract."""
        tag_mgr = TagManager(test_db_path)
        contract_mgr = ContractManager(test_db_path)

        tag_salary = tag_mgr.apply_franchise_tag(
            player_id=100,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            position="QB"
        )

        # Verify contract was created
        contracts = contract_mgr.db_api.get_team_contracts(
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty"
        )

        assert len(contracts) == 1
        contract = contracts[0]
        assert contract['contract_years'] == 1
        assert contract['total_value'] == tag_salary
        assert contract['contract_type'] == "FRANCHISE_TAG"
        assert contract['signing_bonus'] == 0  # Tags have no signing bonus
        assert contract['total_guaranteed'] == tag_salary  # Fully guaranteed

    def test_transition_tag_creates_contract(self, test_db_path):
        """Test that applying transition tag creates 1-year contract."""
        tag_mgr = TagManager(test_db_path)
        contract_mgr = ContractManager(test_db_path)

        tag_salary = tag_mgr.apply_transition_tag(
            player_id=200,
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty",
            position="WR"
        )

        # Verify contract was created
        contracts = contract_mgr.db_api.get_team_contracts(
            team_id=1,
            season=2025,
            dynasty_id="test_dynasty"
        )

        assert len(contracts) == 1
        contract = contracts[0]
        assert contract['contract_type'] == "TRANSITION_TAG"
        assert contract['total_value'] == tag_salary


class TestTagHistory:
    """Test tag history tracking."""

    def test_get_player_franchise_tags(self, test_db_path):
        """Test retrieving player tag history."""
        tag_mgr = TagManager(test_db_path)

        # Apply tags across multiple seasons
        tag_mgr.apply_franchise_tag(
            player_id=100, team_id=1, season=2024,
            dynasty_id="test_dynasty", position="QB"
        )
        tag_mgr.apply_franchise_tag(
            player_id=100, team_id=1, season=2025,
            dynasty_id="test_dynasty", position="QB"
        )
        tag_mgr.apply_franchise_tag(
            player_id=100, team_id=1, season=2026,
            dynasty_id="test_dynasty", position="QB"
        )

        # Get history
        history = tag_mgr._get_player_tag_history(100, 1)

        assert len(history) == 3
        # Should be sorted by season (newest first)
        assert history[0]['season'] == 2026
        assert history[1]['season'] == 2025
        assert history[2]['season'] == 2024

    def test_get_team_tag_count(self, test_db_path):
        """Test getting team's tag usage count."""
        tag_mgr = TagManager(test_db_path)

        # Team applies 1 franchise tag
        tag_mgr.apply_franchise_tag(
            player_id=100, team_id=1, season=2025,
            dynasty_id="test_dynasty", position="QB"
        )

        counts = tag_mgr.get_team_tag_count(1, 2025, "test_dynasty")

        assert counts['franchise'] == 1
        assert counts['transition'] == 0
        assert counts['total'] == 1

    def test_get_team_tag_count_with_transition(self, test_db_path):
        """Test tag count includes transition tags."""
        tag_mgr = TagManager(test_db_path)

        # Team applies transition tag
        tag_mgr.apply_transition_tag(
            player_id=200, team_id=1, season=2025,
            dynasty_id="test_dynasty", position="WR"
        )

        counts = tag_mgr.get_team_tag_count(1, 2025, "test_dynasty")

        assert counts['franchise'] == 0
        assert counts['transition'] == 1
        assert counts['total'] == 1


class TestTagConstants:
    """Test tag manager constants match NFL rules."""

    def test_franchise_tag_constants(self):
        """Test franchise tag constants."""
        assert TagManager.FRANCHISE_TAG_TOP_N == 5
        assert TagManager.SECOND_TAG_MULTIPLIER == 1.20
        assert TagManager.THIRD_TAG_MULTIPLIER == 1.44

    def test_transition_tag_constants(self):
        """Test transition tag constants."""
        assert TagManager.TRANSITION_TAG_TOP_N == 10

    def test_rfa_tender_constants(self):
        """Test RFA tender constants."""
        tag_mgr = TagManager()
        assert tag_mgr.RFA_FIRST_ROUND_TENDER == 4_158_000
        assert tag_mgr.RFA_SECOND_ROUND_TENDER == 3_116_000
        assert tag_mgr.RFA_ORIGINAL_ROUND_TENDER == 2_985_000
        assert tag_mgr.RFA_RIGHT_OF_FIRST_REFUSAL == 2_985_000
        assert tag_mgr.RFA_SALARY_PERCENTAGE == 1.10


class TestDynastyIsolation:
    """Test that tags are properly isolated by dynasty."""

    def test_tags_isolated_by_dynasty(self, test_db_path):
        """Test that tags in different dynasties don't interfere."""
        tag_mgr = TagManager(test_db_path)

        # Apply tag in dynasty 1
        tag_mgr.apply_franchise_tag(
            player_id=100, team_id=1, season=2025,
            dynasty_id="dynasty_1", position="QB"
        )

        # Apply tag in dynasty 2
        tag_mgr.apply_franchise_tag(
            player_id=100, team_id=1, season=2025,
            dynasty_id="dynasty_2", position="QB"
        )

        # Each dynasty should only see their own tags
        db_api = CapDatabaseAPI(test_db_path)

        dynasty1_tags = db_api.get_team_franchise_tags(1, 2025, "dynasty_1")
        dynasty2_tags = db_api.get_team_franchise_tags(1, 2025, "dynasty_2")

        assert len(dynasty1_tags) == 1
        assert len(dynasty2_tags) == 1
        assert dynasty1_tags[0]['dynasty_id'] == "dynasty_1"
        assert dynasty2_tags[0]['dynasty_id'] == "dynasty_2"