"""
Integration tests for PlayerPersonaService and PersonaAPI.

Tests persona generation, distribution, persistence, and display hints.
Part of Tollgate 3: Persona Service.
"""
import json
import os
import tempfile
from collections import Counter

import pytest

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.persona_api import PersonaAPI, PersonaRecord
from src.game_cycle.services.player_persona_service import (
    PlayerPersonaService,
    BASE_WEIGHTS,
)
from src.player_management.player_persona import PlayerPersona, PersonaType


class TestPersonaAPI:
    """Tests for PersonaAPI CRUD operations."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        # Create a team and dynasty for FK constraints
        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield path, conn

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_insert_and_get_persona(self, temp_db):
        """Can insert and retrieve a persona."""
        db_path, _ = temp_db
        api = PersonaAPI(db_path)

        record = PersonaRecord(
            player_id=100,
            persona_type="ring_chaser",
            winning_importance=90,
            money_importance=40,
        )
        result = api.insert_persona("test_dynasty", record)
        assert result is True

        persona = api.get_persona("test_dynasty", 100)
        assert persona is not None
        assert persona["player_id"] == 100
        assert persona["persona_type"] == "ring_chaser"
        assert persona["winning_importance"] == 90
        assert persona["money_importance"] == 40

    def test_dynasty_isolation(self, temp_db):
        """Personas are isolated by dynasty."""
        db_path, conn = temp_db
        api = PersonaAPI(db_path)

        # Create second dynasty
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('other_dynasty', 10, 'Other Dynasty')
        """
        )
        conn.commit()

        # Insert same player_id in different dynasties
        record1 = PersonaRecord(player_id=100, persona_type="ring_chaser")
        record2 = PersonaRecord(player_id=100, persona_type="money_first")

        api.insert_persona("test_dynasty", record1)
        api.insert_persona("other_dynasty", record2)

        # Verify isolation
        p1 = api.get_persona("test_dynasty", 100)
        p2 = api.get_persona("other_dynasty", 100)

        assert p1["persona_type"] == "ring_chaser"
        assert p2["persona_type"] == "money_first"

    def test_update_career_context(self, temp_db):
        """Can update career context fields."""
        db_path, _ = temp_db
        api = PersonaAPI(db_path)

        record = PersonaRecord(
            player_id=100,
            persona_type="ring_chaser",
            career_earnings=10_000_000,
            championship_count=0,
            pro_bowl_count=1,
        )
        api.insert_persona("test_dynasty", record)

        # Update career stats
        result = api.update_career_context(
            "test_dynasty",
            100,
            career_earnings=25_000_000,
            championship_count=1,
            pro_bowl_count=3,
        )
        assert result is True

        persona = api.get_persona("test_dynasty", 100)
        assert persona["career_earnings"] == 25_000_000
        assert persona["championship_count"] == 1
        assert persona["pro_bowl_count"] == 3

    def test_delete_persona(self, temp_db):
        """Can delete a persona."""
        db_path, _ = temp_db
        api = PersonaAPI(db_path)

        record = PersonaRecord(player_id=100, persona_type="ring_chaser")
        api.insert_persona("test_dynasty", record)

        assert api.persona_exists("test_dynasty", 100) is True

        result = api.delete_persona("test_dynasty", 100)
        assert result is True
        assert api.persona_exists("test_dynasty", 100) is False

    def test_batch_insert(self, temp_db):
        """Can insert multiple personas in batch."""
        db_path, _ = temp_db
        api = PersonaAPI(db_path)

        records = [
            PersonaRecord(player_id=100, persona_type="ring_chaser"),
            PersonaRecord(player_id=101, persona_type="money_first"),
            PersonaRecord(player_id=102, persona_type="competitor"),
        ]

        count = api.insert_personas_batch("test_dynasty", records)
        assert count == 3

        assert api.persona_exists("test_dynasty", 100) is True
        assert api.persona_exists("test_dynasty", 101) is True
        assert api.persona_exists("test_dynasty", 102) is True


class TestPersonaGeneration:
    """Tests for persona generation distribution and modifiers."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield path

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_base_distribution(self, temp_db):
        """Distribution roughly matches expected weights over 1000 generations."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        # Generate 1000 personas
        counts: Counter = Counter()
        for i in range(1000):
            persona = service.generate_persona(
                player_id=i,
                age=27,
                overall=75,
                position="WR",
                team_id=10,
            )
            counts[persona.persona_type] += 1

        # Verify distribution (allow ±7% variance for randomness)
        total = sum(counts.values())
        for persona_type, expected_weight in BASE_WEIGHTS.items():
            expected_pct = expected_weight
            actual_pct = (counts[persona_type] / total) * 100
            assert abs(actual_pct - expected_pct) < 7, (
                f"{persona_type.value}: expected ~{expected_pct}%, "
                f"got {actual_pct:.1f}%"
            )

    def test_veteran_ring_chaser_bias(self, temp_db):
        """Veterans (30+) are more likely to be Ring Chasers."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        # Generate personas for young players
        young_ring_chasers = 0
        for i in range(500):
            persona = service.generate_persona(
                player_id=i,
                age=24,
                overall=75,
                position="WR",
                team_id=10,
            )
            if persona.persona_type == PersonaType.RING_CHASER:
                young_ring_chasers += 1

        # Generate personas for veterans
        veteran_ring_chasers = 0
        for i in range(500, 1000):
            persona = service.generate_persona(
                player_id=i,
                age=32,
                overall=75,
                position="WR",
                team_id=10,
            )
            if persona.persona_type == PersonaType.RING_CHASER:
                veteran_ring_chasers += 1

        # Veterans should have higher ring chaser rate
        assert veteran_ring_chasers > young_ring_chasers, (
            f"Veterans should have more ring chasers: "
            f"veterans={veteran_ring_chasers}, young={young_ring_chasers}"
        )

    def test_high_earner_modifier(self, temp_db):
        """High earners ($50M+) are less likely to be Money First."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        # Generate personas for low earners
        low_earner_money_first = 0
        for i in range(500):
            persona = service.generate_persona(
                player_id=i,
                age=28,
                overall=80,
                position="QB",
                team_id=10,
                career_earnings=5_000_000,
            )
            if persona.persona_type == PersonaType.MONEY_FIRST:
                low_earner_money_first += 1

        # Generate personas for high earners
        high_earner_money_first = 0
        for i in range(500, 1000):
            persona = service.generate_persona(
                player_id=i,
                age=28,
                overall=80,
                position="QB",
                team_id=10,
                career_earnings=75_000_000,
            )
            if persona.persona_type == PersonaType.MONEY_FIRST:
                high_earner_money_first += 1

        # Low earners should have higher money first rate
        assert low_earner_money_first > high_earner_money_first, (
            f"Low earners should have more money_first: "
            f"low={low_earner_money_first}, high={high_earner_money_first}"
        )

    def test_persona_persistence(self, temp_db):
        """Personas persist to database and reload correctly."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        # Generate and save
        persona = service.generate_persona(
            player_id=100,
            age=28,
            overall=85,
            position="QB",
            team_id=10,
            birthplace_state="TX",
            college_state="AL",
        )
        service.save_persona(persona)

        # Reload and verify
        loaded = service.get_persona(100)
        assert loaded is not None
        assert loaded.player_id == persona.player_id
        assert loaded.persona_type == persona.persona_type
        assert loaded.money_importance == persona.money_importance
        assert loaded.winning_importance == persona.winning_importance
        assert loaded.birthplace_state == "TX"
        assert loaded.college_state == "AL"


class TestDisplayHints:
    """Tests for display hint generation."""

    @pytest.fixture
    def ring_chaser_persona(self):
        """Create a Ring Chaser persona for testing."""
        return PlayerPersona(
            player_id=100,
            persona_type=PersonaType.RING_CHASER,
            winning_importance=90,
            money_importance=40,
        )

    @pytest.fixture
    def hometown_hero_persona(self):
        """Create a Hometown Hero persona for testing."""
        return PlayerPersona(
            player_id=101,
            persona_type=PersonaType.HOMETOWN_HERO,
            location_importance=95,
            loyalty_importance=85,
            birthplace_state="TX",
            college_state="OK",
        )

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield path

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_own_team_full_details(self, temp_db, ring_chaser_persona):
        """Own team gets full persona details."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)
        hints = service.get_display_hints(ring_chaser_persona, is_own_team=True)

        assert len(hints) >= 1
        assert "Ring Chaser" in hints[0]
        assert any("winning" in h.lower() or "championships" in h.lower() for h in hints)

    def test_other_team_vague_hints(self, temp_db, ring_chaser_persona):
        """Other teams get vague hints only."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)
        hints = service.get_display_hints(ring_chaser_persona, is_own_team=False)

        assert len(hints) >= 1
        # Should NOT reveal "Ring Chaser" label
        assert "Ring Chaser" not in hints[0]
        # Should have vague hint about winning
        assert any("winning" in h.lower() for h in hints)

    def test_hometown_hero_shows_location(self, temp_db, hometown_hero_persona):
        """Hometown Hero shows birthplace/college for own team."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)
        hints = service.get_display_hints(hometown_hero_persona, is_own_team=True)

        # Should include birthplace state
        assert any("TX" in h for h in hints)
        # Should include college state
        assert any("OK" in h for h in hints)

    def test_hometown_hero_hides_location_from_others(self, temp_db, hometown_hero_persona):
        """Hometown Hero hides location from other teams."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)
        hints = service.get_display_hints(hometown_hero_persona, is_own_team=False)

        # Should NOT show specific states
        assert not any("TX" in h for h in hints)
        assert not any("OK" in h for h in hints)


class TestCareerContext:
    """Tests for career context updates."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield path

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_update_career_earnings(self, temp_db):
        """Can update career earnings incrementally."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        # Create and save persona
        persona = service.generate_persona(
            player_id=100, age=28, overall=85, position="QB", team_id=10
        )
        service.save_persona(persona)

        # Update earnings
        service.update_career_context(100, earnings_added=15_000_000)

        # Verify
        loaded = service.get_persona(100)
        assert loaded.career_earnings == 15_000_000

        # Add more
        service.update_career_context(100, earnings_added=10_000_000)
        loaded = service.get_persona(100)
        assert loaded.career_earnings == 25_000_000

    def test_update_championship_count(self, temp_db):
        """Can update championship count."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        # Create and save persona
        persona = service.generate_persona(
            player_id=100, age=28, overall=85, position="QB", team_id=10
        )
        service.save_persona(persona)

        # Win a championship
        service.update_career_context(100, won_championship=True)

        # Verify
        loaded = service.get_persona(100)
        assert loaded.championship_count == 1

        # Win another
        service.update_career_context(100, won_championship=True)
        loaded = service.get_persona(100)
        assert loaded.championship_count == 2


class TestPersonaPreferences:
    """Tests for preference value generation."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield path

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_ring_chaser_high_winning_importance(self, temp_db):
        """Ring Chasers have high winning importance (80-95)."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        # Generate many ring chasers and check their preferences
        ring_chasers_found = 0
        for i in range(200):
            persona = service.generate_persona(
                player_id=i,
                age=32,  # Veteran bias toward ring chaser
                overall=80,
                position="WR",
                team_id=10,
                championship_count=0,  # Ringless veteran bias
            )
            if persona.persona_type == PersonaType.RING_CHASER:
                ring_chasers_found += 1
                # Verify winning importance is high
                assert 80 <= persona.winning_importance <= 95, (
                    f"Ring Chaser winning_importance={persona.winning_importance}"
                )
                # Verify money importance is low-medium
                assert 30 <= persona.money_importance <= 50

        # Should have found at least 10 ring chasers
        assert ring_chasers_found >= 10

    def test_money_first_high_money_importance(self, temp_db):
        """Money First personas have high money importance (85-100)."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        money_first_found = 0
        for i in range(200):
            persona = service.generate_persona(
                player_id=i,
                age=24,  # Young player bias toward money first
                overall=75,
                position="RB",
                team_id=10,
            )
            if persona.persona_type == PersonaType.MONEY_FIRST:
                money_first_found += 1
                # Verify money importance is high
                assert 85 <= persona.money_importance <= 100

        # Should have found at least 20 money first
        assert money_first_found >= 20

    def test_all_importance_values_in_range(self, temp_db):
        """All importance values are 0-100."""
        service = PlayerPersonaService(temp_db, "test_dynasty", 2025)

        for i in range(100):
            persona = service.generate_persona(
                player_id=i,
                age=27,
                overall=75,
                position="WR",
                team_id=10,
            )

            assert 0 <= persona.money_importance <= 100
            assert 0 <= persona.winning_importance <= 100
            assert 0 <= persona.location_importance <= 100
            assert 0 <= persona.playing_time_importance <= 100
            assert 0 <= persona.loyalty_importance <= 100
            assert 0 <= persona.market_size_importance <= 100
            assert 0 <= persona.coaching_fit_importance <= 100
            assert 0 <= persona.relationships_importance <= 100
