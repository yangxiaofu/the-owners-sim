"""Tests for TeamAttractiveness dataclass."""

import pytest
from src.player_management.team_attractiveness import TeamAttractiveness


class TestTeamAttractiveness:
    """Tests for TeamAttractiveness dataclass."""

    def test_create_minimal(self):
        """Can create with only team_id."""
        ta = TeamAttractiveness(team_id=10)
        assert ta.team_id == 10
        assert ta.market_size == 50  # Default

    def test_create_full(self):
        """Can create with all fields."""
        ta = TeamAttractiveness(
            team_id=10,
            market_size=90,
            state_income_tax_rate=0.0,
            weather_score=70,
            state="TX",
            playoff_appearances_5yr=4,
            super_bowl_wins_5yr=1,
            winning_culture_score=85,
            coaching_prestige=80,
            current_season_wins=12,
            current_season_losses=5,
        )
        assert ta.market_size == 90
        assert ta.state == "TX"
        assert ta.super_bowl_wins_5yr == 1

    def test_validate_team_id_range_too_high(self):
        """Team ID must be 1-32."""
        with pytest.raises(ValueError, match="team_id must be 1-32"):
            TeamAttractiveness(team_id=50)

    def test_validate_team_id_range_zero(self):
        """Team ID cannot be zero."""
        with pytest.raises(ValueError, match="team_id must be 1-32"):
            TeamAttractiveness(team_id=0)

    def test_validate_market_size_range_too_high(self):
        """Market size must be 1-100."""
        with pytest.raises(ValueError, match="market_size must be 1-100"):
            TeamAttractiveness(team_id=10, market_size=150)

    def test_validate_market_size_range_too_low(self):
        """Market size cannot be zero."""
        with pytest.raises(ValueError, match="market_size must be 1-100"):
            TeamAttractiveness(team_id=10, market_size=0)

    def test_validate_weather_score_range(self):
        """Weather score must be 1-100."""
        with pytest.raises(ValueError, match="weather_score must be 1-100"):
            TeamAttractiveness(team_id=10, weather_score=0)

    def test_validate_tax_rate_range_too_high(self):
        """Tax rate must be 0.0-0.15."""
        with pytest.raises(ValueError, match="state_income_tax_rate must be 0.0-0.15"):
            TeamAttractiveness(team_id=10, state_income_tax_rate=0.20)

    def test_validate_tax_rate_range_negative(self):
        """Tax rate cannot be negative."""
        with pytest.raises(ValueError, match="state_income_tax_rate must be 0.0-0.15"):
            TeamAttractiveness(team_id=10, state_income_tax_rate=-0.01)

    def test_validate_playoff_appearances_range(self):
        """Playoff appearances must be 0-5."""
        with pytest.raises(ValueError, match="playoff_appearances_5yr must be 0-5"):
            TeamAttractiveness(team_id=10, playoff_appearances_5yr=6)

    def test_validate_super_bowl_wins_range(self):
        """Super Bowl wins must be 0-5."""
        with pytest.raises(ValueError, match="super_bowl_wins_5yr must be 0-5"):
            TeamAttractiveness(team_id=10, super_bowl_wins_5yr=6)

    def test_validate_winning_culture_score_range(self):
        """Winning culture score must be 0-100."""
        with pytest.raises(ValueError, match="winning_culture_score must be 0-100"):
            TeamAttractiveness(team_id=10, winning_culture_score=101)

    def test_validate_negative_wins(self):
        """Current season wins cannot be negative."""
        with pytest.raises(ValueError, match="current_season_wins cannot be negative"):
            TeamAttractiveness(team_id=10, current_season_wins=-1)

    def test_validate_negative_losses(self):
        """Current season losses cannot be negative."""
        with pytest.raises(ValueError, match="current_season_losses cannot be negative"):
            TeamAttractiveness(team_id=10, current_season_losses=-1)


class TestContenderScore:
    """Tests for contender_score property."""

    def test_contender_score_no_games(self):
        """No games played returns mid-range score."""
        ta = TeamAttractiveness(team_id=10)
        # 50 (default current record) * 0.4 + 0 + 0 + 50 * 0.1 = 25
        assert ta.contender_score == 25

    def test_contender_score_perfect_team(self):
        """Perfect team gets high score."""
        ta = TeamAttractiveness(
            team_id=10,
            playoff_appearances_5yr=5,
            super_bowl_wins_5yr=2,
            winning_culture_score=95,
            current_season_wins=17,
            current_season_losses=0,
        )
        # 100*0.4 + 100*0.3 + 40*0.2 + 95*0.1 = 40 + 30 + 8 + 9.5 = 87.5
        assert ta.contender_score >= 85

    def test_contender_score_bad_team(self):
        """Bad team gets low score."""
        ta = TeamAttractiveness(
            team_id=10,
            playoff_appearances_5yr=0,
            super_bowl_wins_5yr=0,
            winning_culture_score=20,
            current_season_wins=2,
            current_season_losses=15,
        )
        # (2/17)*100*0.4 + 0 + 0 + 20*0.1 = 4.7 + 2 = ~7
        assert ta.contender_score <= 20

    def test_contender_score_mid_range_team(self):
        """Average team gets middle score."""
        ta = TeamAttractiveness(
            team_id=10,
            playoff_appearances_5yr=2,
            super_bowl_wins_5yr=0,
            winning_culture_score=50,
            current_season_wins=8,
            current_season_losses=8,
        )
        # (8/16)*100*0.4 + (2/5)*100*0.3 + 0 + 50*0.1 = 20 + 12 + 5 = 37
        assert 30 <= ta.contender_score <= 50


class TestTaxAdvantageScore:
    """Tests for tax_advantage_score property."""

    def test_no_tax_state(self):
        """No-tax state gets 100."""
        ta = TeamAttractiveness(team_id=10, state_income_tax_rate=0.0)
        assert ta.tax_advantage_score == 100

    def test_max_tax_state(self):
        """Max tax state (13%) gets 0."""
        ta = TeamAttractiveness(team_id=10, state_income_tax_rate=0.13)
        assert ta.tax_advantage_score == 0

    def test_mid_tax_state(self):
        """Mid-range tax (6.5%) gets proportional score (~50)."""
        ta = TeamAttractiveness(team_id=10, state_income_tax_rate=0.065)
        assert 45 <= ta.tax_advantage_score <= 55

    def test_high_tax_state(self):
        """High tax state (10%) gets low score."""
        ta = TeamAttractiveness(team_id=10, state_income_tax_rate=0.10)
        # (0.13 - 0.10) / 0.13 * 100 = 23
        assert ta.tax_advantage_score <= 30


class TestTeamAttractivenessSerialization:
    """Tests for serialization methods."""

    def test_to_dict_includes_computed(self):
        """to_dict includes computed properties."""
        ta = TeamAttractiveness(team_id=10, state_income_tax_rate=0.0)
        d = ta.to_dict()

        assert "contender_score" in d
        assert "tax_advantage_score" in d
        assert d["tax_advantage_score"] == 100

    def test_to_dict_all_fields(self):
        """to_dict includes all fields."""
        ta = TeamAttractiveness(
            team_id=22,
            market_size=45,
            state="MI",
            playoff_appearances_5yr=2,
        )
        d = ta.to_dict()

        assert d["team_id"] == 22
        assert d["market_size"] == 45
        assert d["state"] == "MI"
        assert d["playoff_appearances_5yr"] == 2

    def test_from_dict(self):
        """from_dict creates correct object."""
        data = {
            "team_id": 10,
            "market_size": 90,
            "state": "TX",
            "state_income_tax_rate": 0.0,
        }
        ta = TeamAttractiveness.from_dict(data)

        assert ta.team_id == 10
        assert ta.market_size == 90
        assert ta.state == "TX"
        assert ta.state_income_tax_rate == 0.0

    def test_round_trip(self):
        """to_dict -> from_dict preserves data."""
        original = TeamAttractiveness(
            team_id=22,
            market_size=45,
            state="MI",
            playoff_appearances_5yr=2,
            current_season_wins=10,
            current_season_losses=7,
        )

        restored = TeamAttractiveness.from_dict(original.to_dict())

        assert restored.team_id == original.team_id
        assert restored.market_size == original.market_size
        assert restored.state == original.state
        assert restored.playoff_appearances_5yr == original.playoff_appearances_5yr
        assert restored.current_season_wins == original.current_season_wins

    def test_from_db_row(self):
        """from_db_row creates correct object from dict."""
        row = {
            "team_id": 15,
            "market_size": 60,
            "weather_score": 75,
        }
        ta = TeamAttractiveness.from_db_row(row)
        assert ta.team_id == 15
        assert ta.market_size == 60
        assert ta.weather_score == 75


class TestTeamAttractivenessEdgeCases:
    """Edge case tests for TeamAttractiveness."""

    def test_boundary_team_ids(self):
        """Team IDs 1 and 32 are valid."""
        ta1 = TeamAttractiveness(team_id=1)
        ta32 = TeamAttractiveness(team_id=32)
        assert ta1.team_id == 1
        assert ta32.team_id == 32

    def test_boundary_market_size(self):
        """Market sizes 1 and 100 are valid."""
        ta1 = TeamAttractiveness(team_id=10, market_size=1)
        ta100 = TeamAttractiveness(team_id=10, market_size=100)
        assert ta1.market_size == 1
        assert ta100.market_size == 100

    def test_zero_playoff_appearances(self):
        """Zero playoff appearances is valid."""
        ta = TeamAttractiveness(team_id=10, playoff_appearances_5yr=0)
        assert ta.playoff_appearances_5yr == 0

    def test_max_playoff_appearances(self):
        """Five playoff appearances is valid."""
        ta = TeamAttractiveness(team_id=10, playoff_appearances_5yr=5)
        assert ta.playoff_appearances_5yr == 5