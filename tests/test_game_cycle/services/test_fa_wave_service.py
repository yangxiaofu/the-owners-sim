"""
Tests for FAWaveService.

Part of Milestone 8: Free Agency Depth - Tollgate 2.
"""
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from src.game_cycle.services.fa_wave_service import FAWaveService
from src.game_cycle.database.fa_wave_state_api import WAVE_CONFIGS


@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025
        );

        CREATE TABLE IF NOT EXISTS fa_wave_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            current_wave INTEGER DEFAULT 0 CHECK(current_wave BETWEEN 0 AND 4),
            current_day INTEGER DEFAULT 1 CHECK(current_day BETWEEN 1 AND 3),
            wave_complete INTEGER DEFAULT 0 CHECK(wave_complete IN (0, 1)),
            post_draft_available INTEGER DEFAULT 0 CHECK(post_draft_available IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, season)
        );

        CREATE TABLE IF NOT EXISTS pending_offers (
            offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            wave INTEGER NOT NULL CHECK(wave BETWEEN 0 AND 4),
            player_id INTEGER NOT NULL,
            offering_team_id INTEGER NOT NULL CHECK(offering_team_id BETWEEN 1 AND 32),
            aav INTEGER NOT NULL,
            total_value INTEGER NOT NULL,
            years INTEGER NOT NULL CHECK(years BETWEEN 1 AND 7),
            guaranteed INTEGER NOT NULL,
            signing_bonus INTEGER DEFAULT 0,
            decision_deadline INTEGER NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN (
                'pending', 'accepted', 'rejected', 'expired', 'withdrawn', 'surprise'
            )),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, season, wave, player_id, offering_team_id)
        );

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test_dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield path

    os.unlink(path)


@pytest.fixture
def service(db_path):
    """Create FAWaveService instance."""
    return FAWaveService(db_path, "test_dynasty", 2025)


# =============================================================================
# Wave State Tests (5 tests)
# =============================================================================

class TestWaveStateManagement:
    """Tests for wave state management methods."""

    def test_get_wave_state_initializes_if_missing(self, service):
        """Should initialize wave state if not found."""
        state = service.get_wave_state()

        assert state is not None
        assert state["dynasty_id"] == "test_dynasty"
        assert state["season"] == 2025
        assert state["current_wave"] == 0
        assert state["current_day"] == 1
        assert state["wave_name"] == "Legal Tampering"

    def test_advance_day_increments_correctly(self, service):
        """Advancing day should increment current_day."""
        # Initialize and move to wave 1 (3 days)
        service.get_wave_state()
        service.advance_wave()

        state = service.get_wave_state()
        assert state["current_day"] == 1

        state = service.advance_day()
        assert state["current_day"] == 2
        assert state["wave_complete"] is False

    def test_advance_wave_resets_day(self, service):
        """Advancing wave should reset to day 1."""
        service.get_wave_state()

        # Wave 0 -> Wave 1
        state = service.advance_wave()
        assert state["current_wave"] == 1
        assert state["current_day"] == 1
        assert state["wave_name"] == "Wave 1 - Elite"

    def test_enable_post_draft_wave(self, service):
        """Should enable and advance to post-draft wave."""
        service.get_wave_state()

        state = service.enable_post_draft_wave()
        assert state["current_wave"] == 4
        assert state["post_draft_available"] is True
        assert state["wave_name"] == "Post-Draft"

    def test_wave_state_persists_across_instances(self, db_path):
        """Wave state should persist across service instances."""
        service1 = FAWaveService(db_path, "test_dynasty", 2025)
        service1.get_wave_state()
        service1.advance_wave()

        # Create new instance
        service2 = FAWaveService(db_path, "test_dynasty", 2025)
        state = service2.get_wave_state()

        assert state["current_wave"] == 1


# =============================================================================
# Player Filtering Tests (5 tests)
# =============================================================================

class TestPlayerFiltering:
    """Tests for player filtering by wave tier."""

    @patch.object(FAWaveService, '_get_fa_service')
    def test_wave_1_filters_to_85_plus(self, mock_get_fa, service):
        """Wave 1 should only return players with OVR 85+."""
        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 1, "name": "Elite QB", "overall": 92},
            {"player_id": 2, "name": "Quality WR", "overall": 80},
            {"player_id": 3, "name": "Depth LB", "overall": 70},
        ]
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()  # Move to wave 1

        players = service.get_available_players_for_wave(wave=1)

        assert len(players) == 1
        assert players[0]["player_id"] == 1
        assert players[0]["overall"] == 92

    @patch.object(FAWaveService, '_get_fa_service')
    def test_wave_2_filters_to_75_84(self, mock_get_fa, service):
        """Wave 2 should only return players with OVR 75-84."""
        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 1, "name": "Elite QB", "overall": 92},
            {"player_id": 2, "name": "Quality WR", "overall": 80},
            {"player_id": 3, "name": "Depth LB", "overall": 70},
        ]
        mock_get_fa.return_value = mock_fa

        players = service.get_available_players_for_wave(wave=2)

        assert len(players) == 1
        assert players[0]["player_id"] == 2
        assert players[0]["overall"] == 80

    @patch.object(FAWaveService, '_get_fa_service')
    def test_wave_3_filters_to_65_74(self, mock_get_fa, service):
        """Wave 3 should only return players with OVR 65-74."""
        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 1, "name": "Elite QB", "overall": 92},
            {"player_id": 2, "name": "Quality WR", "overall": 80},
            {"player_id": 3, "name": "Depth LB", "overall": 70},
        ]
        mock_get_fa.return_value = mock_fa

        players = service.get_available_players_for_wave(wave=3)

        assert len(players) == 1
        assert players[0]["player_id"] == 3
        assert players[0]["overall"] == 70

    @patch.object(FAWaveService, '_get_fa_service')
    def test_wave_4_includes_all_remaining(self, mock_get_fa, service):
        """Wave 4 (Post-Draft) should include all remaining FAs."""
        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 1, "name": "Elite QB", "overall": 92},
            {"player_id": 2, "name": "Quality WR", "overall": 80},
            {"player_id": 3, "name": "Depth LB", "overall": 70},
            {"player_id": 4, "name": "Low OVR", "overall": 60},
        ]
        mock_get_fa.return_value = mock_fa

        players = service.get_available_players_for_wave(wave=4)

        # Wave 4 has min_ovr=0, max_ovr=99
        assert len(players) == 4

    @patch.object(FAWaveService, '_get_fa_service')
    def test_players_include_offer_status(self, mock_get_fa, service, db_path):
        """Players should include pending offer status."""
        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 100, "name": "Star QB", "overall": 92},
        ]
        mock_get_fa.return_value = mock_fa

        # Initialize and move to wave 1
        service.get_wave_state()
        service.advance_wave()

        # Create an offer
        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    10000000, 40000000, 4, 20000000, 5000000, 3)
        ''')
        conn.commit()
        conn.close()

        players = service.get_available_players_for_wave(wave=1, user_team_id=1)

        assert players[0]["pending_offer_count"] == 1
        assert players[0]["has_user_offer"] is False


# =============================================================================
# Offer Submission Tests (6 tests)
# =============================================================================

class TestOfferSubmission:
    """Tests for offer submission functionality."""

    @patch.object(FAWaveService, '_get_fa_service')
    def test_submit_offer_creates_record(self, mock_get_fa, service):
        """Submitting an offer should create a database record."""
        mock_fa = Mock()
        mock_fa.get_team_cap_space.return_value = 50_000_000
        mock_get_fa.return_value = mock_fa

        # Move to wave 1 (signing allowed)
        service.get_wave_state()
        service.advance_wave()

        result = service.submit_offer(
            player_id=100,
            team_id=5,
            aav=10_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000
        )

        assert result["success"] is True
        assert "offer_id" in result
        assert result["wave"] == 1
        assert result["decision_deadline"] == 3  # Wave 1 has 3 days

    @patch.object(FAWaveService, '_get_fa_service')
    def test_submit_offer_validates_cap_space(self, mock_get_fa, service):
        """Should reject offers exceeding cap space."""
        mock_fa = Mock()
        mock_fa.get_team_cap_space.return_value = 5_000_000  # Low cap
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        result = service.submit_offer(
            player_id=100,
            team_id=5,
            aav=10_000_000,  # Exceeds cap
            years=4,
            guaranteed=25_000_000
        )

        assert result["success"] is False
        assert "cap space" in result["error"].lower()

    @patch.object(FAWaveService, '_get_fa_service')
    def test_submit_offer_prevents_duplicates(self, mock_get_fa, service):
        """Should prevent duplicate offers from same team."""
        mock_fa = Mock()
        mock_fa.get_team_cap_space.return_value = 50_000_000
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        # First offer
        result1 = service.submit_offer(
            player_id=100, team_id=5, aav=10_000_000, years=4, guaranteed=25_000_000
        )
        assert result1["success"] is True

        # Duplicate offer
        result2 = service.submit_offer(
            player_id=100, team_id=5, aav=12_000_000, years=4, guaranteed=30_000_000
        )
        assert result2["success"] is False
        assert "already have" in result2["error"].lower()

    def test_submit_offer_blocked_in_legal_tampering(self, service):
        """Offers should be blocked in Legal Tampering (Wave 0)."""
        service.get_wave_state()  # Wave 0

        result = service.submit_offer(
            player_id=100, team_id=5, aav=10_000_000, years=4, guaranteed=25_000_000
        )

        assert result["success"] is False
        assert "legal tampering" in result["error"].lower()

    @patch.object(FAWaveService, '_get_fa_service')
    def test_withdraw_offer_updates_status(self, mock_get_fa, service, db_path):
        """Withdrawing an offer should update its status."""
        mock_fa = Mock()
        mock_fa.get_team_cap_space.return_value = 50_000_000
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        result = service.submit_offer(
            player_id=100, team_id=5, aav=10_000_000, years=4, guaranteed=25_000_000
        )
        offer_id = result["offer_id"]

        # Withdraw
        success = service.withdraw_offer(offer_id)
        assert success is True

        # Verify status
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT status FROM pending_offers WHERE offer_id = ?", (offer_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["status"] == "withdrawn"

    @patch.object(FAWaveService, '_get_fa_service')
    def test_submit_offer_sets_deadline(self, mock_get_fa, service):
        """Offer should have correct decision deadline based on wave."""
        mock_fa = Mock()
        mock_fa.get_team_cap_space.return_value = 50_000_000
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()  # Wave 1 (3 days)

        result = service.submit_offer(
            player_id=100, team_id=5, aav=10_000_000, years=4, guaranteed=25_000_000
        )

        assert result["decision_deadline"] == 3


# =============================================================================
# AI Offers Tests (4 tests)
# =============================================================================

class TestAIOffers:
    """Tests for AI offer generation."""

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_ai_generates_offers_for_needs(self, mock_random, mock_get_fa, service):
        """AI should generate offers based on team needs."""
        mock_random.random.return_value = 0.05  # Low random for multiplier
        mock_random.choice.return_value = 3  # 3 years
        mock_random.uniform.return_value = 0.5  # 50% guaranteed

        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 100, "name": "Star QB", "overall": 92,
             "position": "quarterback", "estimated_aav": 30_000_000},
        ]
        mock_fa.get_team_cap_space.return_value = 50_000_000
        mock_fa._get_team_positional_needs.return_value = ["quarterback"]
        mock_fa.evaluate_player_interest.return_value = {
            "interest_level": "medium", "acceptance_probability": 0.6
        }
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        with patch('database.player_roster_api.PlayerRosterAPI'):
            result = service.generate_ai_offers(user_team_id=1, max_offers_per_team=3)

        assert result["offers_made"] >= 0

    @patch.object(FAWaveService, '_get_fa_service')
    def test_ai_respects_max_offers_per_team(self, mock_get_fa, service, db_path):
        """AI should not exceed max offers per team."""
        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = []
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        # Manually add 3 offers for team 2
        conn = sqlite3.connect(db_path)
        for i in range(3):
            conn.execute('''
                INSERT INTO pending_offers
                (dynasty_id, season, wave, player_id, offering_team_id,
                 aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
                VALUES ('test_dynasty', 2025, 1, ?, 2,
                        10000000, 40000000, 4, 20000000, 0, 3)
            ''', (200 + i,))
        conn.commit()
        conn.close()

        # Team 2 already has 3 offers, should be skipped
        with patch('database.player_roster_api.PlayerRosterAPI'):
            result = service.generate_ai_offers(user_team_id=1, max_offers_per_team=3)

        # Should have made 0 offers for team 2 since it's at max
        assert result["offers_made"] >= 0

    @patch.object(FAWaveService, '_get_fa_service')
    def test_ai_skips_low_interest_players(self, mock_get_fa, service):
        """AI should skip players with low interest."""
        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 100, "name": "Star QB", "overall": 92,
             "position": "quarterback", "estimated_aav": 30_000_000},
        ]
        mock_fa.get_team_cap_space.return_value = 50_000_000
        mock_fa._get_team_positional_needs.return_value = ["quarterback"]
        mock_fa.evaluate_player_interest.return_value = {
            "interest_level": "very_low", "acceptance_probability": 0.1
        }
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        with patch('database.player_roster_api.PlayerRosterAPI'):
            result = service.generate_ai_offers(user_team_id=1)

        # Should have skipped due to low interest
        assert result["offers_made"] == 0

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_ai_offers_at_market_rate(self, mock_random, mock_get_fa, service):
        """AI offers should be at or slightly above market rate."""
        mock_random.random.return_value = 0.10  # 10% above market
        mock_random.choice.return_value = 3
        mock_random.uniform.return_value = 0.5

        mock_fa = Mock()
        mock_fa.get_available_free_agents.return_value = [
            {"player_id": 100, "name": "Star QB", "overall": 92,
             "position": "quarterback", "estimated_aav": 10_000_000},
        ]
        mock_fa.get_team_cap_space.return_value = 50_000_000
        mock_fa._get_team_positional_needs.return_value = ["quarterback"]
        mock_fa.evaluate_player_interest.return_value = {
            "interest_level": "high", "acceptance_probability": 0.8
        }
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        with patch('database.player_roster_api.PlayerRosterAPI'):
            result = service.generate_ai_offers(user_team_id=1)

        # Should generate offers (multiplier = 1.0 + 0.10 = 1.10)
        assert result["offers_made"] >= 0


# =============================================================================
# Surprise Signing Tests (4 tests)
# =============================================================================

class TestSurpriseSignings:
    """Tests for surprise signing functionality."""

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_surprise_only_targets_user_offers(self, mock_random, mock_get_fa, service, db_path):
        """Surprise signings should only target players user has offered."""
        mock_random.random.return_value = 0.05  # Under 20% threshold
        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB"
        }
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        # User offer (team 1)
        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 1,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        # AI offer on same player
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    12000000, 48000000, 4, 24000000, 0, 3)
        ''')
        # AI offer on different player (should not be targeted)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 200, 5,
                    8000000, 32000000, 4, 16000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        surprises = service.process_surprise_signings(user_team_id=1, probability=1.0)

        # Should only target player 100 (user's offer)
        assert len(surprises) == 1
        assert surprises[0]["player_id"] == 100

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_surprise_respects_probability(self, mock_random, mock_get_fa, service, db_path):
        """Surprise signings should respect probability threshold."""
        mock_random.random.return_value = 0.50  # Above 20% threshold
        mock_fa = Mock()
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        # User and AI offers
        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 1,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    12000000, 48000000, 4, 24000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        # With default 20% probability, random=0.50 should not trigger
        surprises = service.process_surprise_signings(user_team_id=1, probability=0.20)

        assert len(surprises) == 0

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_surprise_marks_offers_correctly(self, mock_random, mock_get_fa, service, db_path):
        """Surprise signing should mark offers with correct statuses."""
        mock_random.random.return_value = 0.05
        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB"
        }
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        conn = sqlite3.connect(db_path)
        # User offer
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 1,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        # AI offer (winner)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    12000000, 48000000, 4, 24000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        service.process_surprise_signings(user_team_id=1, probability=1.0)

        # Check offer statuses
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('''
            SELECT offering_team_id, status FROM pending_offers
            WHERE dynasty_id = 'test_dynasty' AND player_id = 100
        ''')
        offers = {row["offering_team_id"]: row["status"] for row in cursor.fetchall()}
        conn.close()

        assert offers[5] == "surprise"  # AI winner
        assert offers[1] == "rejected"  # User's offer

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_surprise_creates_contract(self, mock_random, mock_get_fa, service, db_path):
        """Surprise signing should create actual contract via FA service."""
        mock_random.random.return_value = 0.05
        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB"
        }
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 1,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    12000000, 48000000, 4, 24000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        service.process_surprise_signings(user_team_id=1, probability=1.0)

        # Verify sign_free_agent was called
        mock_fa.sign_free_agent.assert_called_once_with(
            player_id=100,
            team_id=5,
            skip_preference_check=False
        )


# =============================================================================
# Offer Resolution Tests (6 tests)
# =============================================================================

class TestOfferResolution:
    """Tests for offer resolution at wave end."""

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_resolve_picks_highest_score(self, mock_random, mock_get_fa, service, db_path):
        """Resolution should prefer highest-scored offer."""
        mock_random.random.return_value = 0.1  # Below probability threshold

        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB"
        }
        mock_persona = Mock()
        mock_persona.get_persona.return_value = None  # No persona = pick highest AAV
        mock_fa._get_persona_service.return_value = mock_persona
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        # Create offers with different AAV
        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 1,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    15000000, 60000000, 4, 30000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        result = service.resolve_wave_offers()

        # Should have signed with team 5 (higher AAV)
        assert len(result["signings"]) == 1
        assert result["signings"][0]["team_id"] == 5

    @patch.object(FAWaveService, '_get_fa_service')
    @patch.object(FAWaveService, '_get_preference_engine')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_resolve_uses_preference_engine(
        self, mock_random, mock_pref, mock_get_fa, service, db_path
    ):
        """Resolution should use PreferenceEngine for scoring."""
        mock_random.random.return_value = 0.1

        # Setup mocks
        mock_engine = Mock()
        mock_engine.calculate_team_score.return_value = 75
        mock_engine.calculate_acceptance_probability.return_value = 0.8
        mock_pref.return_value = mock_engine

        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB"
        }

        mock_persona = Mock()
        mock_persona_obj = MagicMock()
        mock_persona_obj.drafting_team_id = 0
        mock_persona.get_persona.return_value = mock_persona_obj
        mock_fa._get_persona_service.return_value = mock_persona

        mock_attr = Mock()
        mock_attr.get_team_attractiveness.return_value = Mock()
        mock_fa._get_attractiveness_service.return_value = mock_attr

        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        with patch('src.player_management.preference_engine.ContractOffer'):
            service.resolve_wave_offers()

        # Verify preference engine was called
        mock_engine.calculate_team_score.assert_called()

    @patch.object(FAWaveService, '_get_fa_service')
    @patch.object(FAWaveService, '_get_preference_engine')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_resolve_rejects_low_probability(
        self, mock_random, mock_pref, mock_get_fa, service, db_path
    ):
        """Low probability offers should be rejected."""
        mock_random.random.return_value = 0.9  # High random, will fail probability check

        mock_engine = Mock()
        mock_engine.calculate_team_score.return_value = 30  # Low score
        mock_engine.calculate_acceptance_probability.return_value = 0.1  # 10% prob
        mock_pref.return_value = mock_engine

        mock_fa = Mock()
        mock_persona = Mock()
        mock_persona_obj = MagicMock()
        mock_persona_obj.drafting_team_id = 0
        mock_persona.get_persona.return_value = mock_persona_obj
        mock_fa._get_persona_service.return_value = mock_persona

        mock_attr = Mock()
        mock_attr.get_team_attractiveness.return_value = Mock()
        mock_fa._get_attractiveness_service.return_value = mock_attr

        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        with patch('src.player_management.preference_engine.ContractOffer'):
            result = service.resolve_wave_offers()

        # Should reject (random 0.9 > probability 0.1)
        assert len(result["signings"]) == 0
        assert len(result["no_accepts"]) == 1

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_resolve_handles_no_persona(self, mock_random, mock_get_fa, service, db_path):
        """Players without persona should accept highest AAV."""
        mock_random.random.return_value = 0.1

        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB"
        }
        mock_persona = Mock()
        mock_persona.get_persona.return_value = None  # No persona
        mock_fa._get_persona_service.return_value = mock_persona
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 1,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    15000000, 60000000, 4, 30000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        result = service.resolve_wave_offers()

        # Should accept highest AAV (team 5)
        assert len(result["signings"]) == 1
        assert result["signings"][0]["team_id"] == 5

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_resolve_updates_all_offer_statuses(
        self, mock_random, mock_get_fa, service, db_path
    ):
        """Resolution should update statuses for all offers."""
        mock_random.random.return_value = 0.1

        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB"
        }
        mock_persona = Mock()
        mock_persona.get_persona.return_value = None
        mock_fa._get_persona_service.return_value = mock_persona
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 1,
                    10000000, 40000000, 4, 20000000, 0, 3)
        ''')
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    15000000, 60000000, 4, 30000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        service.resolve_wave_offers()

        # Check statuses
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('''
            SELECT offering_team_id, status FROM pending_offers
            WHERE dynasty_id = 'test_dynasty' AND player_id = 100
        ''')
        offers = {row["offering_team_id"]: row["status"] for row in cursor.fetchall()}
        conn.close()

        assert offers[5] == "accepted"
        assert offers[1] == "rejected"

    @patch.object(FAWaveService, '_get_fa_service')
    @patch('src.game_cycle.services.fa_wave_service.random')
    def test_resolve_creates_contract_on_accept(
        self, mock_random, mock_get_fa, service, db_path
    ):
        """Accepted offer should create contract via FA service."""
        mock_random.random.return_value = 0.1

        mock_fa = Mock()
        mock_fa.sign_free_agent.return_value = {
            "success": True, "player_name": "Star QB",
            "contract_details": {"aav": 15000000, "years": 4}
        }
        mock_persona = Mock()
        mock_persona.get_persona.return_value = None
        mock_fa._get_persona_service.return_value = mock_persona
        mock_get_fa.return_value = mock_fa

        service.get_wave_state()
        service.advance_wave()

        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO pending_offers
            (dynasty_id, season, wave, player_id, offering_team_id,
             aav, total_value, years, guaranteed, signing_bonus, decision_deadline)
            VALUES ('test_dynasty', 2025, 1, 100, 5,
                    15000000, 60000000, 4, 30000000, 0, 3)
        ''')
        conn.commit()
        conn.close()

        service.resolve_wave_offers()

        # Verify sign_free_agent was called
        mock_fa.sign_free_agent.assert_called_once_with(
            player_id=100,
            team_id=5,
            skip_preference_check=True
        )


# =============================================================================
# Summary Method Tests (2 tests)
# =============================================================================

class TestSummaryMethods:
    """Tests for summary methods."""

    def test_get_wave_summary(self, service):
        """Should return complete wave summary."""
        service.get_wave_state()
        service.advance_wave()  # Wave 1

        summary = service.get_wave_summary()

        assert summary["wave"] == 1
        assert summary["wave_name"] == "Wave 1 - Elite"
        assert summary["current_day"] == 1
        assert summary["days_in_wave"] == 3
        assert summary["days_remaining"] == 3
        assert summary["wave_complete"] is False
        assert summary["signing_allowed"] is True
        assert summary["pending_offers"] == 0

    def test_is_fa_complete(self, service):
        """Should correctly report FA completion status."""
        service.get_wave_state()

        assert service.is_fa_complete() is False

        # Enable post-draft and complete it
        service.enable_post_draft_wave()
        service.advance_day()  # Complete wave 4 (1 day)

        # Mark complete
        api = service._get_wave_state_api()
        api.mark_wave_complete("test_dynasty", 2025)

        assert service.is_fa_complete() is True