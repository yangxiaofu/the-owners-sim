"""
Tests for PendingOffersAPI.

Part of Milestone 8: Free Agency Depth - Tollgate 1.
"""
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.pending_offers_api import PendingOffersAPI, PendingOffer


@pytest.fixture
def db_path():
    """Create a temporary database with the schema."""
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
def api(db_path):
    """Create API instance."""
    return PendingOffersAPI(db_path)


class TestCreateOffer:
    """Tests for creating offers."""

    def test_create_offer_returns_id(self, api):
        """Creating an offer should return the offer ID."""
        offer_id = api.create_offer(
            dynasty_id="test_dynasty",
            season=2025,
            wave=1,
            player_id=100,
            offering_team_id=5,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            decision_deadline=3
        )
        assert offer_id is not None
        assert offer_id > 0

    def test_create_offer_stores_all_fields(self, api):
        """All fields should be stored correctly."""
        offer_id = api.create_offer(
            dynasty_id="test_dynasty",
            season=2025,
            wave=2,
            player_id=200,
            offering_team_id=10,
            aav=15_000_000,
            total_value=60_000_000,
            years=4,
            guaranteed=35_000_000,
            signing_bonus=8_000_000,
            decision_deadline=2
        )

        offer = api.get_offer_by_id(offer_id)
        assert offer["dynasty_id"] == "test_dynasty"
        assert offer["season"] == 2025
        assert offer["wave"] == 2
        assert offer["player_id"] == 200
        assert offer["offering_team_id"] == 10
        assert offer["aav"] == 15_000_000
        assert offer["total_value"] == 60_000_000
        assert offer["years"] == 4
        assert offer["guaranteed"] == 35_000_000
        assert offer["signing_bonus"] == 8_000_000
        assert offer["decision_deadline"] == 2
        assert offer["status"] == "pending"

    def test_duplicate_offer_raises_error(self, api):
        """Same team offering to same player in same wave should fail."""
        api.create_offer(
            dynasty_id="test_dynasty",
            season=2025,
            wave=1,
            player_id=100,
            offering_team_id=5,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=0,
            decision_deadline=3
        )

        with pytest.raises(sqlite3.IntegrityError):
            api.create_offer(
                dynasty_id="test_dynasty",
                season=2025,
                wave=1,
                player_id=100,
                offering_team_id=5,
                aav=12_000_000,  # Different terms
                total_value=48_000_000,
                years=4,
                guaranteed=30_000_000,
                signing_bonus=0,
                decision_deadline=3
            )


class TestGetOffers:
    """Tests for retrieving offers."""

    def test_get_offers_by_player(self, api):
        """Should get all offers for a player."""
        # Create offers from multiple teams
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=10,
            aav=12_000_000, total_value=48_000_000, years=4,
            guaranteed=30_000_000, signing_bonus=0, decision_deadline=3
        )

        offers = api.get_offers_by_player("test_dynasty", 100)
        assert len(offers) == 2
        # Should be ordered by AAV descending
        assert offers[0]["aav"] == 12_000_000
        assert offers[1]["aav"] == 10_000_000

    def test_get_offers_by_player_with_status_filter(self, api):
        """Should filter by status."""
        offer_id = api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        api.update_offer_status(offer_id, "accepted")

        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=10,
            aav=12_000_000, total_value=48_000_000, years=4,
            guaranteed=30_000_000, signing_bonus=0, decision_deadline=3
        )

        pending = api.get_offers_by_player("test_dynasty", 100, status="pending")
        assert len(pending) == 1
        assert pending[0]["offering_team_id"] == 10

    def test_get_offers_by_team(self, api):
        """Should get all offers submitted by a team."""
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=200, offering_team_id=5,
            aav=8_000_000, total_value=32_000_000, years=4,
            guaranteed=20_000_000, signing_bonus=0, decision_deadline=3
        )

        offers = api.get_offers_by_team("test_dynasty", 5)
        assert len(offers) == 2

    def test_get_wave_offers(self, api):
        """Should get all offers for a specific wave."""
        # Wave 1 offers
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        # Wave 2 offer
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=2,
            player_id=200, offering_team_id=10,
            aav=8_000_000, total_value=32_000_000, years=4,
            guaranteed=20_000_000, signing_bonus=0, decision_deadline=2
        )

        wave1 = api.get_wave_offers("test_dynasty", 2025, 1)
        assert len(wave1) == 1
        assert wave1[0]["wave"] == 1

        wave2 = api.get_wave_offers("test_dynasty", 2025, 2)
        assert len(wave2) == 1
        assert wave2[0]["wave"] == 2


class TestUpdateStatus:
    """Tests for updating offer status."""

    def test_update_status_to_accepted(self, api):
        """Should update status to accepted."""
        offer_id = api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )

        result = api.update_offer_status(offer_id, "accepted")
        assert result is True

        offer = api.get_offer_by_id(offer_id)
        assert offer["status"] == "accepted"
        assert offer["resolved_at"] is not None

    def test_invalid_status_raises_error(self, api):
        """Should raise error for invalid status."""
        offer_id = api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )

        with pytest.raises(ValueError):
            api.update_offer_status(offer_id, "invalid_status")

    def test_bulk_update_status(self, api):
        """Should update multiple offers at once."""
        id1 = api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        id2 = api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=10,
            aav=12_000_000, total_value=48_000_000, years=4,
            guaranteed=30_000_000, signing_bonus=0, decision_deadline=3
        )

        count = api.bulk_update_status([id1, id2], "rejected")
        assert count == 2

        offer1 = api.get_offer_by_id(id1)
        offer2 = api.get_offer_by_id(id2)
        assert offer1["status"] == "rejected"
        assert offer2["status"] == "rejected"

    def test_withdraw_offer(self, api):
        """Should withdraw an offer."""
        offer_id = api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )

        result = api.withdraw_offer(offer_id)
        assert result is True

        offer = api.get_offer_by_id(offer_id)
        assert offer["status"] == "withdrawn"


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_pending_offers_count(self, api):
        """Should count pending offers."""
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=200, offering_team_id=5,
            aav=8_000_000, total_value=32_000_000, years=4,
            guaranteed=20_000_000, signing_bonus=0, decision_deadline=3
        )

        count = api.get_pending_offers_count("test_dynasty")
        assert count == 2

        count_team = api.get_pending_offers_count("test_dynasty", team_id=5)
        assert count_team == 2

    def test_get_players_with_pending_offers(self, api):
        """Should return unique player IDs with pending offers."""
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=10,
            aav=12_000_000, total_value=48_000_000, years=4,
            guaranteed=30_000_000, signing_bonus=0, decision_deadline=3
        )
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=200, offering_team_id=5,
            aav=8_000_000, total_value=32_000_000, years=4,
            guaranteed=20_000_000, signing_bonus=0, decision_deadline=3
        )

        players = api.get_players_with_pending_offers("test_dynasty", 2025, 1)
        assert len(players) == 2
        assert 100 in players
        assert 200 in players

    def test_check_existing_offer(self, api):
        """Should find existing offer for team/player combo."""
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )

        existing = api.check_existing_offer("test_dynasty", 2025, 1, 100, 5)
        assert existing is not None
        assert existing["aav"] == 10_000_000

        not_existing = api.check_existing_offer("test_dynasty", 2025, 1, 100, 10)
        assert not_existing is None

    def test_expire_old_offers(self, api):
        """Should expire offers past deadline."""
        # Offer with deadline day 1
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=1
        )
        # Offer with deadline day 3
        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=200, offering_team_id=10,
            aav=8_000_000, total_value=32_000_000, years=4,
            guaranteed=20_000_000, signing_bonus=0, decision_deadline=3
        )

        # Expire offers with deadline < day 2
        expired = api.expire_old_offers("test_dynasty", 2025, 1, deadline=2)
        assert expired == 1

        offers = api.get_wave_offers("test_dynasty", 2025, 1, status="pending")
        assert len(offers) == 1
        assert offers[0]["player_id"] == 200


class TestDynastyIsolation:
    """Tests for dynasty isolation."""

    def test_offers_isolated_by_dynasty(self, api, db_path):
        """Offers should be isolated by dynasty."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        api.create_offer(
            dynasty_id="test_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )
        api.create_offer(
            dynasty_id="other_dynasty", season=2025, wave=1,
            player_id=100, offering_team_id=5,
            aav=10_000_000, total_value=40_000_000, years=4,
            guaranteed=25_000_000, signing_bonus=0, decision_deadline=3
        )

        test_offers = api.get_offers_by_player("test_dynasty", 100)
        other_offers = api.get_offers_by_player("other_dynasty", 100)

        assert len(test_offers) == 1
        assert len(other_offers) == 1
        assert test_offers[0]["dynasty_id"] == "test_dynasty"
        assert other_offers[0]["dynasty_id"] == "other_dynasty"
