"""
Shared fixtures for factor tests.

Provides common player data, contexts, and test utilities.
"""

import pytest
import json
import tempfile
from pathlib import Path

from contract_valuation.context import ValuationContext


@pytest.fixture
def default_context():
    """Default 2025 valuation context."""
    return ValuationContext.create_default_2025()


@pytest.fixture
def sample_qb_data():
    """Elite QB with full stats and attributes."""
    return {
        "player_id": 1001,
        "name": "Patrick Star",
        "position": "QB",
        "age": 28,
        "overall_rating": 95,
        "contract_year": False,
        "birthdate": "1996-09-17",
        "archetype": "pocket_passer_qb",
        "development_curve": "normal",
        "attributes": {
            "overall": 95,
            "accuracy": 94,
            "arm_strength": 96,
            "pocket_presence": 92,
            "composure": 90,
            "vision": 88,
            "speed": 78,
            "strength": 75,
            "agility": 82,
            "stamina": 88,
            "acceleration": 80,
            "awareness": 92,
            "discipline": 85,
            "experience": 7,
            "football_iq": 90,
            "potential": 98,
        },
        "stats": {
            "passing_yards": 4500,
            "passing_tds": 35,
            "completion_pct": 68.5,
            "passer_rating": 105.2,
            "interceptions": 10,
            "games_played": 17,
        },
        "games_played": 17,
    }


@pytest.fixture
def sample_rb_data():
    """Quality RB with rushing stats."""
    return {
        "player_id": 1002,
        "name": "Rusher Jones",
        "position": "RB",
        "age": 25,
        "overall_rating": 82,
        "contract_year": True,
        "birthdate": "1999-03-15",
        "development_curve": "normal",
        "attributes": {
            "overall": 82,
            "speed": 90,
            "elusiveness": 85,
            "vision": 80,
            "carrying": 82,
            "acceleration": 88,
            "strength": 75,
            "agility": 86,
            "stamina": 85,
            "awareness": 78,
            "discipline": 75,
            "composure": 80,
            "experience": 4,
            "football_iq": 78,
            "potential": 85,
        },
        "stats": {
            "rushing_yards": 1100,
            "rushing_tds": 9,
            "yards_per_carry": 4.5,
            "receptions": 45,
            "receiving_yards": 380,
            "fumbles": 2,
            "games_played": 16,
        },
        "games_played": 16,
    }


@pytest.fixture
def sample_wr_data():
    """Quality WR with receiving stats."""
    return {
        "player_id": 1003,
        "name": "Speed Demon",
        "position": "WR",
        "age": 27,
        "overall_rating": 85,
        "contract_year": False,
        "birthdate": "1997-07-22",
        "development_curve": "normal",
        "attributes": {
            "overall": 85,
            "speed": 95,
            "hands": 88,
            "route_running": 86,
            "release": 84,
            "acceleration": 92,
            "strength": 70,
            "agility": 90,
            "stamina": 82,
            "awareness": 82,
            "discipline": 80,
            "composure": 78,
            "experience": 5,
            "football_iq": 80,
            "potential": 88,
        },
        "stats": {
            "receiving_yards": 1200,
            "receptions": 85,
            "receiving_tds": 8,
            "yards_per_reception": 14.1,
            "catch_rate": 68,
            "games_played": 16,
        },
        "games_played": 16,
    }


@pytest.fixture
def young_player_data():
    """22-year-old CB for age testing."""
    return {
        "player_id": 1004,
        "name": "Young Corner",
        "position": "CB",
        "age": 22,
        "overall_rating": 78,
        "contract_year": False,
        "birthdate": "2002-11-05",
        "development_curve": "early",
        "attributes": {
            "overall": 78,
            "coverage": 80,
            "speed": 92,
            "press": 75,
            "agility": 88,
            "ball_skills": 77,
            "strength": 70,
            "stamina": 85,
            "acceleration": 90,
            "awareness": 72,
            "discipline": 70,
            "composure": 75,
            "experience": 1,
            "football_iq": 72,
            "potential": 92,
        },
        "stats": {
            "passes_defended": 12,
            "interceptions": 3,
            "tackles": 55,
            "forced_fumbles": 1,
            "games_played": 15,
        },
        "games_played": 15,
    }


@pytest.fixture
def veteran_player_data():
    """33-year-old LB for age testing."""
    return {
        "player_id": 1005,
        "name": "Old Linebacker",
        "position": "LB",
        "age": 33,
        "overall_rating": 80,
        "contract_year": False,
        "birthdate": "1991-04-18",
        "development_curve": "late",
        "attributes": {
            "overall": 80,
            "tackling": 88,
            "coverage": 75,
            "awareness": 92,
            "speed": 78,
            "pursuit": 82,
            "strength": 82,
            "agility": 75,
            "stamina": 78,
            "discipline": 90,
            "composure": 92,
            "experience": 11,
            "football_iq": 94,
            "potential": 80,
        },
        "stats": {
            "tackles": 95,
            "sacks": 2.5,
            "tfl": 8,
            "interceptions": 1,
            "passes_defended": 4,
            "games_played": 16,
        },
        "games_played": 16,
    }


@pytest.fixture
def edge_rusher_data():
    """Elite EDGE rusher for position mapping tests."""
    return {
        "player_id": 1006,
        "name": "Sack Master",
        "position": "LOLB",
        "age": 27,
        "overall_rating": 92,
        "contract_year": False,
        "birthdate": "1997-08-12",
        "development_curve": "normal",
        "attributes": {
            "overall": 92,
            "pass_rush": 94,
            "speed": 88,
            "strength": 86,
            "finesse_moves": 90,
            "power_moves": 85,
            "agility": 85,
            "stamina": 82,
            "acceleration": 87,
            "awareness": 85,
            "discipline": 82,
            "composure": 84,
            "experience": 5,
            "football_iq": 84,
            "potential": 93,
        },
        "stats": {
            "sacks": 14,
            "tackles": 55,
            "qb_hits": 18,
            "tfl": 12,
            "forced_fumbles": 3,
            "games_played": 17,
        },
        "games_played": 17,
    }


@pytest.fixture
def backup_player_data():
    """Backup-tier player for testing low ratings."""
    return {
        "player_id": 1007,
        "name": "Bench Warmer",
        "position": "WR",
        "age": 26,
        "overall_rating": 65,
        "contract_year": False,
        "attributes": {
            "overall": 65,
            "speed": 82,
            "hands": 68,
            "route_running": 62,
            "release": 60,
            "acceleration": 80,
            "strength": 65,
            "agility": 78,
            "stamina": 75,
            "awareness": 62,
            "discipline": 65,
            "composure": 60,
            "experience": 3,
            "football_iq": 62,
            "potential": 70,
        },
        "stats": {
            "receiving_yards": 180,
            "receptions": 15,
            "receiving_tds": 1,
            "yards_per_reception": 12.0,
            "catch_rate": 58,
            "games_played": 14,
        },
        "games_played": 14,
    }


@pytest.fixture
def minimal_player_data():
    """Minimal player data with only required fields."""
    return {
        "player_id": 1008,
        "name": "Minimal Mike",
        "position": "TE",
    }


@pytest.fixture
def archetypes_path(tmp_path):
    """Temporary directory with test archetype JSONs."""
    archetypes_dir = tmp_path / "archetypes"
    archetypes_dir.mkdir()

    # Create pocket_passer_qb archetype
    pocket_passer = {
        "name": "Pocket Passer",
        "position": "QB",
        "peak_age_range": [28, 34],
        "development_curve": "normal",
        "key_attributes": ["accuracy", "arm_strength", "pocket_presence"],
    }
    with open(archetypes_dir / "pocket_passer_qb.json", "w") as f:
        json.dump(pocket_passer, f)

    # Create power_back_rb archetype
    power_back = {
        "name": "Power Back",
        "position": "RB",
        "peak_age_range": [24, 28],
        "development_curve": "normal",
        "key_attributes": ["strength", "carrying", "vision"],
    }
    with open(archetypes_dir / "power_back_rb.json", "w") as f:
        json.dump(power_back, f)

    return archetypes_dir
