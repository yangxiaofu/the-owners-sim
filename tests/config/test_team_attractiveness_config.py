"""Tests for team_attractiveness_static.json configuration."""

import json
import pytest
from pathlib import Path


class TestTeamAttractivenessConfig:
    """Validate team attractiveness configuration data."""

    @pytest.fixture
    def config_data(self):
        """Load the config file."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "config"
            / "team_attractiveness_static.json"
        )
        with open(config_path) as f:
            return json.load(f)

    def test_all_32_teams_present(self, config_data):
        """Config has exactly 32 teams."""
        assert len(config_data) == 32
        for team_id in range(1, 33):
            assert str(team_id) in config_data, f"Team {team_id} missing"

    def test_required_fields(self, config_data):
        """Each team has all required fields."""
        required = {
            "team_name",
            "state",
            "market_size",
            "state_income_tax_rate",
            "weather_score",
            "metro_population",
        }
        for team_id, team in config_data.items():
            missing = required - set(team.keys())
            assert not missing, f"Team {team_id} missing: {missing}"

    def test_market_size_range(self, config_data):
        """Market size is 1-100 for all teams."""
        for team_id, team in config_data.items():
            assert (
                1 <= team["market_size"] <= 100
            ), f"Team {team_id}: market_size {team['market_size']}"

    def test_tax_rate_range(self, config_data):
        """Tax rate is 0.0-0.14 for all teams."""
        for team_id, team in config_data.items():
            assert (
                0.0 <= team["state_income_tax_rate"] <= 0.14
            ), f"Team {team_id}: rate {team['state_income_tax_rate']}"

    def test_weather_score_range(self, config_data):
        """Weather score is 1-100 for all teams."""
        for team_id, team in config_data.items():
            assert (
                1 <= team["weather_score"] <= 100
            ), f"Team {team_id}: weather {team['weather_score']}"

    def test_metro_population_positive(self, config_data):
        """Metro population is positive for all teams."""
        for team_id, team in config_data.items():
            assert (
                team["metro_population"] > 0
            ), f"Team {team_id}: invalid population {team['metro_population']}"

    def test_state_code_valid(self, config_data):
        """State codes are 2-letter abbreviations."""
        for team_id, team in config_data.items():
            assert (
                len(team["state"]) == 2
            ), f"Team {team_id}: invalid state {team['state']}"
            assert team["state"].isupper(), f"Team {team_id}: state not uppercase"

    def test_no_tax_states_correct(self, config_data):
        """Teams in no-tax states have 0.0 tax rate."""
        no_tax_teams = {
            "2": "FL",  # Miami Dolphins
            "9": "TX",  # Houston Texans
            "11": "FL",  # Jacksonville Jaguars
            "12": "TN",  # Tennessee Titans
            "15": "NV",  # Las Vegas Raiders
            "17": "TX",  # Dallas Cowboys
            "28": "FL",  # Tampa Bay Buccaneers
            "32": "WA",  # Seattle Seahawks
        }
        for team_id, state in no_tax_teams.items():
            assert config_data[team_id]["state"] == state
            assert (
                config_data[team_id]["state_income_tax_rate"] == 0.0
            ), f"Team {team_id} should have 0% tax"

    def test_california_teams_high_tax(self, config_data):
        """California teams have ~13.3% tax rate."""
        ca_teams = ["16", "30", "31"]  # Chargers, Rams, 49ers
        for team_id in ca_teams:
            assert config_data[team_id]["state"] == "CA"
            assert config_data[team_id]["state_income_tax_rate"] >= 0.13

    def test_market_size_distribution(self, config_data):
        """Big markets have high scores, small markets have low."""
        # NYC teams should be 90+
        assert config_data["4"]["market_size"] >= 90  # Jets
        assert config_data["18"]["market_size"] >= 90  # Giants

        # LA teams should be 90+
        assert config_data["16"]["market_size"] >= 90  # Chargers
        assert config_data["30"]["market_size"] >= 90  # Rams

        # Green Bay should be lowest
        assert config_data["23"]["market_size"] <= 30  # Packers

    def test_weather_extremes(self, config_data):
        """Florida teams have high weather, northern teams low."""
        # Florida teams should have high weather scores
        assert config_data["2"]["weather_score"] >= 80  # Miami
        assert config_data["11"]["weather_score"] >= 75  # Jacksonville
        assert config_data["28"]["weather_score"] >= 80  # Tampa Bay

        # Northern teams should have low weather scores
        assert config_data["23"]["weather_score"] <= 30  # Green Bay
        assert config_data["1"]["weather_score"] <= 30  # Buffalo
