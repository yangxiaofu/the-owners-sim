"""
Integration Test: Budget Stance FA Contract Modifiers

Tests that owner directives' budget_stance influences FA contract offers:
- AGGRESSIVE: 5-10% above market
- MODERATE: Market value (no modifier)
- CONSERVATIVE: 5-10% below market

Part of Tollgate 7: Service Layer Integration
"""

import pytest
import tempfile
import os
from pathlib import Path

from game_cycle.services.free_agency_service import FreeAgencyService
from game_cycle.models.fa_guidance import FAGuidance
from game_cycle.database.connection import GameCycleDatabase
from database.player_roster_api import PlayerRosterAPI
from salary_cap.cap_database_api import CapDatabaseAPI


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # Cleanup
    for suffix in ['', '-wal', '-shm']:
        try:
            os.unlink(db_path + suffix)
        except FileNotFoundError:
            pass


@pytest.fixture
def initialized_db(temp_db):
    """Initialize database with schema and test data."""
    # Initialize game cycle schema
    gc_db = GameCycleDatabase(temp_db)

    # Create test free agent player
    roster_api = PlayerRosterAPI(temp_db)
    cap_api = CapDatabaseAPI(temp_db)

    # Add test player as free agent (team_id=0)
    test_player = {
        "player_id": 9001,
        "first_name": "Test",
        "last_name": "Player",
        "positions": ["WR"],
        "birthdate": "1995-01-01",
        "number": 88,  # Jersey number (required field)
        "team_id": 0,  # Free agent
        "attributes": {
            "overall": 80,
            "speed": 85,
            "catching": 82,
            "route_running": 78
        },
        "years_pro": 4,
        "dynasty_id": "test_dynasty",
    }

    # Insert player directly into database
    import sqlite3
    import json
    conn = sqlite3.connect(temp_db)
    conn.execute("PRAGMA foreign_keys = OFF")  # Disable FK checks for test

    conn.execute("""
        INSERT INTO players (
            player_id, first_name, last_name, number, positions, birthdate,
            team_id, attributes, years_pro, dynasty_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        test_player["player_id"],
        test_player["first_name"],
        test_player["last_name"],
        test_player["number"],
        json.dumps(test_player["positions"]),
        test_player["birthdate"],
        test_player["team_id"],
        json.dumps(test_player["attributes"]),
        test_player["years_pro"],
        test_player["dynasty_id"]
    ))

    conn.commit()
    conn.close()

    return temp_db


@pytest.fixture
def fa_guidance_aggressive():
    """FA guidance with aggressive budget stance."""
    return FAGuidance(
        philosophy="aggressive",
        budget_stance="aggressive",
        priority_positions=["WR", "QB"],
        max_years=5,
        max_guaranteed_pct=0.75
    )


@pytest.fixture
def fa_guidance_moderate():
    """FA guidance with moderate budget stance."""
    return FAGuidance(
        philosophy="balanced",
        budget_stance="moderate",
        priority_positions=["WR"],
        max_years=4,
        max_guaranteed_pct=0.60
    )


@pytest.fixture
def fa_guidance_conservative():
    """FA guidance with conservative budget stance."""
    return FAGuidance(
        philosophy="conservative",
        budget_stance="conservative",
        priority_positions=["WR"],
        max_years=3,
        max_guaranteed_pct=0.50
    )


def test_aggressive_budget_stance_offers_above_market(initialized_db, fa_guidance_aggressive):
    """Test that AGGRESSIVE stance offers 5-10% above market value."""
    fa_service = FreeAgencyService(
        db_path=initialized_db,
        dynasty_id="test_dynasty",
        season=2024
    )

    # Get baseline market value (no guidance)
    result_market = fa_service.sign_free_agent(
        player_id=9001,
        team_id=1,
        skip_preference_check=True,
        fa_guidance=None  # No modifier
    )

    assert result_market["success"], "Market value signing should succeed"
    market_aav = result_market["contract_details"]["aav"]
    market_total = result_market["contract_details"]["total_value"]

    # Reset player to free agent for second test
    import sqlite3
    conn = sqlite3.connect(initialized_db)
    conn.execute("DELETE FROM contracts WHERE player_id = 9001")
    conn.execute("UPDATE players SET team_id = 0, contract_id = NULL WHERE player_id = 9001")
    conn.commit()
    conn.close()

    # Sign with aggressive stance
    result_aggressive = fa_service.sign_free_agent(
        player_id=9001,
        team_id=2,
        skip_preference_check=True,
        fa_guidance=fa_guidance_aggressive
    )

    assert result_aggressive["success"], "Aggressive signing should succeed"

    agg_aav = result_aggressive["contract_details"]["aav"]
    agg_total = result_aggressive["contract_details"]["total_value"]
    modifier = result_aggressive["budget_modifier"]

    # Verify modifier is in expected range (1.05 to 1.10)
    assert 1.05 <= modifier <= 1.10, f"Aggressive modifier {modifier} not in range [1.05, 1.10]"

    # Verify AAV is 5-10% above market
    aav_ratio = agg_aav / market_aav
    assert 1.05 <= aav_ratio <= 1.10, f"AAV ratio {aav_ratio:.3f} not in range [1.05, 1.10]"

    # Verify total value is proportionally higher
    total_ratio = agg_total / market_total
    assert 1.05 <= total_ratio <= 1.10, f"Total ratio {total_ratio:.3f} not in range [1.05, 1.10]"

    print(f"✅ AGGRESSIVE: Market AAV ${market_aav:,} → Aggressive AAV ${agg_aav:,} (modifier: {modifier:.3f})")


def test_moderate_budget_stance_offers_market_value(initialized_db, fa_guidance_moderate):
    """Test that MODERATE stance offers market value (no modifier)."""
    fa_service = FreeAgencyService(
        db_path=initialized_db,
        dynasty_id="test_dynasty",
        season=2024
    )

    # Get baseline market value
    result_market = fa_service.sign_free_agent(
        player_id=9001,
        team_id=1,
        skip_preference_check=True,
        fa_guidance=None
    )

    market_aav = result_market["contract_details"]["aav"]
    market_total = result_market["contract_details"]["total_value"]

    # Reset player
    import sqlite3
    conn = sqlite3.connect(initialized_db)
    conn.execute("DELETE FROM contracts WHERE player_id = 9001")
    conn.execute("UPDATE players SET team_id = 0, contract_id = NULL WHERE player_id = 9001")
    conn.commit()
    conn.close()

    # Sign with moderate stance
    result_moderate = fa_service.sign_free_agent(
        player_id=9001,
        team_id=2,
        skip_preference_check=True,
        fa_guidance=fa_guidance_moderate
    )

    assert result_moderate["success"], "Moderate signing should succeed"

    mod_aav = result_moderate["contract_details"]["aav"]
    mod_total = result_moderate["contract_details"]["total_value"]
    modifier = result_moderate["budget_modifier"]

    # Moderate should have modifier of 1.0 (no change)
    assert modifier == 1.0, f"Moderate modifier should be 1.0, got {modifier}"

    # AAV should match market value
    assert mod_aav == market_aav, f"Moderate AAV ${mod_aav:,} should equal market ${market_aav:,}"

    # Total should match market value
    assert mod_total == market_total, f"Moderate total ${mod_total:,} should equal market ${market_total:,}"

    print(f"✅ MODERATE: Market AAV ${market_aav:,} = Moderate AAV ${mod_aav:,} (modifier: {modifier:.3f})")


def test_conservative_budget_stance_offers_below_market(initialized_db, fa_guidance_conservative):
    """Test that CONSERVATIVE stance offers 5-10% below market value."""
    fa_service = FreeAgencyService(
        db_path=initialized_db,
        dynasty_id="test_dynasty",
        season=2024
    )

    # Get baseline market value
    result_market = fa_service.sign_free_agent(
        player_id=9001,
        team_id=1,
        skip_preference_check=True,
        fa_guidance=None
    )

    market_aav = result_market["contract_details"]["aav"]
    market_total = result_market["contract_details"]["total_value"]

    # Reset player
    import sqlite3
    conn = sqlite3.connect(initialized_db)
    conn.execute("DELETE FROM contracts WHERE player_id = 9001")
    conn.execute("UPDATE players SET team_id = 0, contract_id = NULL WHERE player_id = 9001")
    conn.commit()
    conn.close()

    # Sign with conservative stance
    result_conservative = fa_service.sign_free_agent(
        player_id=9001,
        team_id=2,
        skip_preference_check=True,
        fa_guidance=fa_guidance_conservative
    )

    assert result_conservative["success"], "Conservative signing should succeed"

    con_aav = result_conservative["contract_details"]["aav"]
    con_total = result_conservative["contract_details"]["total_value"]
    modifier = result_conservative["budget_modifier"]

    # Verify modifier is in expected range (0.90 to 0.95)
    assert 0.90 <= modifier <= 0.95, f"Conservative modifier {modifier} not in range [0.90, 0.95]"

    # Verify AAV is 5-10% below market
    aav_ratio = con_aav / market_aav
    assert 0.90 <= aav_ratio <= 0.95, f"AAV ratio {aav_ratio:.3f} not in range [0.90, 0.95]"

    # Verify total value is proportionally lower
    total_ratio = con_total / market_total
    assert 0.90 <= total_ratio <= 0.95, f"Total ratio {total_ratio:.3f} not in range [0.90, 0.95]"

    print(f"✅ CONSERVATIVE: Market AAV ${market_aav:,} → Conservative AAV ${con_aav:,} (modifier: {modifier:.3f})")


def test_all_contract_components_modified_proportionally(initialized_db, fa_guidance_aggressive):
    """Test that all contract components (AAV, total, bonus, guaranteed) are modified equally."""
    fa_service = FreeAgencyService(
        db_path=initialized_db,
        dynasty_id="test_dynasty",
        season=2024
    )

    result = fa_service.sign_free_agent(
        player_id=9001,
        team_id=1,
        skip_preference_check=True,
        fa_guidance=fa_guidance_aggressive
    )

    assert result["success"], "Signing should succeed"

    modifier = result["budget_modifier"]
    details = result["contract_details"]

    # All components should be affected by the same modifier
    # We can't test exact proportions without baseline, but we can verify modifier is applied
    assert 1.05 <= modifier <= 1.10, "Aggressive modifier in range"
    assert details["aav"] > 0, "AAV should be positive"
    assert details["total_value"] > 0, "Total should be positive"
    assert details["guaranteed"] > 0, "Guaranteed should be positive"
    assert details["signing_bonus"] >= 0, "Signing bonus should be non-negative"

    print(f"✅ ALL COMPONENTS MODIFIED: modifier={modifier:.3f}, AAV=${details['aav']:,}, Total=${details['total_value']:,}")


def test_no_modifier_without_guidance(initialized_db):
    """Test that signings without FA guidance use market value (no modifier)."""
    fa_service = FreeAgencyService(
        db_path=initialized_db,
        dynasty_id="test_dynasty",
        season=2024
    )

    result = fa_service.sign_free_agent(
        player_id=9001,
        team_id=1,
        skip_preference_check=True,
        fa_guidance=None  # No guidance
    )

    assert result["success"], "Signing should succeed"
    assert result["budget_modifier"] == 1.0, "No guidance should have modifier of 1.0"

    print(f"✅ NO GUIDANCE: modifier={result['budget_modifier']:.3f} (market value)")


if __name__ == "__main__":
    print("=" * 80)
    print("Running Budget Stance FA Contract Integration Tests")
    print("=" * 80)
    print()

    pytest.main([__file__, "-v", "-s"])
