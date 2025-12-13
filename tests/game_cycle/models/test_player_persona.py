"""Tests for PlayerPersona and PersonaType."""

import pytest
from src.player_management.player_persona import PersonaType, PlayerPersona


class TestPersonaType:
    """Tests for PersonaType enum."""

    def test_persona_type_count(self):
        """Should have exactly 8 persona types."""
        assert len(PersonaType) == 8

    def test_all_persona_types_have_string_values(self):
        """All persona types have snake_case string values."""
        for persona in PersonaType:
            assert isinstance(persona.value, str)
            assert persona.value == persona.value.lower()

    def test_persona_type_values(self):
        """Verify all expected persona types exist."""
        expected = {
            "ring_chaser",
            "hometown_hero",
            "money_first",
            "big_market",
            "small_market",
            "legacy_builder",
            "competitor",
            "system_fit",
        }
        actual = {p.value for p in PersonaType}
        assert actual == expected

    def test_persona_type_from_string(self):
        """Can create PersonaType from string value."""
        assert PersonaType("ring_chaser") == PersonaType.RING_CHASER
        assert PersonaType("money_first") == PersonaType.MONEY_FIRST


class TestPlayerPersona:
    """Tests for PlayerPersona dataclass."""

    def test_create_minimal_persona(self):
        """Can create persona with only required fields."""
        persona = PlayerPersona(player_id=100, persona_type=PersonaType.MONEY_FIRST)
        assert persona.player_id == 100
        assert persona.persona_type == PersonaType.MONEY_FIRST
        assert persona.money_importance == 50  # Default

    def test_create_full_persona(self):
        """Can create persona with all fields."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.HOMETOWN_HERO,
            money_importance=40,
            winning_importance=60,
            location_importance=90,
            birthplace_state="TX",
            college_state="TX",
            drafting_team_id=10,
            career_earnings=50_000_000,
            championship_count=1,
            pro_bowl_count=3,
        )
        assert persona.location_importance == 90
        assert persona.birthplace_state == "TX"
        assert persona.drafting_team_id == 10
        assert persona.career_earnings == 50_000_000

    def test_validate_importance_range_too_high(self):
        """Importance values must be 0-100."""
        with pytest.raises(
            ValueError, match="money_importance must be between 0 and 100"
        ):
            PlayerPersona(
                player_id=100,
                persona_type=PersonaType.MONEY_FIRST,
                money_importance=150,
            )

    def test_validate_negative_importance(self):
        """Importance values cannot be negative."""
        with pytest.raises(ValueError):
            PlayerPersona(
                player_id=100,
                persona_type=PersonaType.MONEY_FIRST,
                winning_importance=-10,
            )

    def test_validate_team_id_range(self):
        """Drafting team ID must be 1-32."""
        with pytest.raises(ValueError, match="drafting_team_id must be 1-32"):
            PlayerPersona(
                player_id=100,
                persona_type=PersonaType.LEGACY_BUILDER,
                drafting_team_id=50,
            )

    def test_validate_team_id_zero(self):
        """Drafting team ID cannot be zero."""
        with pytest.raises(ValueError, match="drafting_team_id must be 1-32"):
            PlayerPersona(
                player_id=100,
                persona_type=PersonaType.LEGACY_BUILDER,
                drafting_team_id=0,
            )

    def test_validate_negative_career_earnings(self):
        """Career earnings cannot be negative."""
        with pytest.raises(ValueError, match="career_earnings cannot be negative"):
            PlayerPersona(
                player_id=100,
                persona_type=PersonaType.MONEY_FIRST,
                career_earnings=-1000,
            )

    def test_validate_negative_championship_count(self):
        """Championship count cannot be negative."""
        with pytest.raises(ValueError, match="championship_count cannot be negative"):
            PlayerPersona(
                player_id=100,
                persona_type=PersonaType.RING_CHASER,
                championship_count=-1,
            )

    def test_validate_negative_pro_bowl_count(self):
        """Pro bowl count cannot be negative."""
        with pytest.raises(ValueError, match="pro_bowl_count cannot be negative"):
            PlayerPersona(
                player_id=100,
                persona_type=PersonaType.RING_CHASER,
                pro_bowl_count=-1,
            )

    def test_null_drafting_team_allowed(self):
        """Drafting team ID can be None."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.MONEY_FIRST,
            drafting_team_id=None,
        )
        assert persona.drafting_team_id is None


class TestPlayerPersonaSerialization:
    """Tests for serialization methods."""

    def test_to_dict(self):
        """to_dict returns correct dictionary."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.RING_CHASER,
            winning_importance=85,
        )
        d = persona.to_dict()

        assert d["player_id"] == 100
        assert d["persona_type"] == "ring_chaser"
        assert d["winning_importance"] == 85
        assert d["money_importance"] == 50  # Default

    def test_from_dict(self):
        """from_dict creates correct persona."""
        data = {
            "player_id": 200,
            "persona_type": "big_market",
            "market_size_importance": 90,
        }
        persona = PlayerPersona.from_dict(data)

        assert persona.player_id == 200
        assert persona.persona_type == PersonaType.BIG_MARKET
        assert persona.market_size_importance == 90

    def test_from_dict_with_enum(self):
        """from_dict works when persona_type is already an enum."""
        data = {
            "player_id": 200,
            "persona_type": PersonaType.BIG_MARKET,
            "market_size_importance": 90,
        }
        persona = PlayerPersona.from_dict(data)
        assert persona.persona_type == PersonaType.BIG_MARKET

    def test_round_trip_serialization(self):
        """to_dict -> from_dict preserves all data."""
        original = PlayerPersona(
            player_id=300,
            persona_type=PersonaType.COMPETITOR,
            playing_time_importance=95,
            birthplace_state="CA",
            career_earnings=25_000_000,
        )

        restored = PlayerPersona.from_dict(original.to_dict())

        assert restored.player_id == original.player_id
        assert restored.persona_type == original.persona_type
        assert restored.playing_time_importance == original.playing_time_importance
        assert restored.birthplace_state == original.birthplace_state
        assert restored.career_earnings == original.career_earnings

    def test_from_db_row(self):
        """from_db_row creates correct persona from dict."""
        row = {
            "player_id": 400,
            "persona_type": "system_fit",
            "coaching_fit_importance": 85,
        }
        persona = PlayerPersona.from_db_row(row)
        assert persona.player_id == 400
        assert persona.persona_type == PersonaType.SYSTEM_FIT

    def test_to_db_dict(self):
        """to_db_dict returns same as to_dict."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.HOMETOWN_HERO,
        )
        assert persona.to_db_dict() == persona.to_dict()


class TestPlayerPersonaProperties:
    """Tests for computed properties."""

    def test_primary_preference_money(self):
        """Primary preference returns highest weight."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.MONEY_FIRST,
            money_importance=95,
            winning_importance=30,
        )
        assert persona.primary_preference == "money"

    def test_primary_preference_winning(self):
        """Primary preference for ring chaser."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.RING_CHASER,
            winning_importance=90,
            money_importance=40,
        )
        assert persona.primary_preference == "winning"

    def test_primary_preference_location(self):
        """Primary preference for hometown hero."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.HOMETOWN_HERO,
            location_importance=95,
            money_importance=40,
            winning_importance=40,
        )
        assert persona.primary_preference == "location"

    def test_primary_preference_playing_time(self):
        """Primary preference for competitor."""
        persona = PlayerPersona(
            player_id=100,
            persona_type=PersonaType.COMPETITOR,
            playing_time_importance=90,
        )
        assert persona.primary_preference == "playing_time"