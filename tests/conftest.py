"""
Pytest configuration for test discovery and imports.

Provides fixtures for testing including:
- Database setup/teardown
- Salary cap test fixtures
- Mock players and teams
"""

import sys
from pathlib import Path
import pytest
import sqlite3
import tempfile
import os


# Determine paths
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
tests_path = project_root / "tests"


def pytest_configure(config):
    """Configure pytest - runs very early in startup.

    IMPORTANT: Project root MUST come before tests/ to prevent shadowing
    of packages like game_cycle_ui by tests/game_cycle_ui.
    """
    # Clear any cached game_cycle_ui modules that may have been imported from tests/
    to_remove = [key for key in sys.modules.keys() if key.startswith('game_cycle_ui')]
    for key in to_remove:
        del sys.modules[key]

    # Filter out tests directory and any duplicates, keeping first occurrence
    seen = set()
    new_path = []
    for p in sys.path:
        if p not in seen and p != str(tests_path):
            seen.add(p)
            new_path.append(p)

    # Ensure project root and src are at the front
    for path in [str(src_path), str(project_root)]:
        if path in new_path:
            new_path.remove(path)

    # Insert at front: project_root, then src
    new_path.insert(0, str(src_path))
    new_path.insert(0, str(project_root))

    sys.path[:] = new_path


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def test_db_path():
    """
    Create temporary database for testing.

    Yields:
        Path to temporary database file

    Cleanup:
        Removes database after test
    """
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def test_db_with_schema(test_db_path):
    """
    Create temporary database with salary cap schema initialized.

    Yields:
        Path to database with schema

    Uses:
        002_salary_cap_schema.sql migration
    """
    from salary_cap.cap_database_api import CapDatabaseAPI

    # Initialize database (will run migration)
    db_api = CapDatabaseAPI(test_db_path)

    yield test_db_path

    # Cleanup handled by test_db_path fixture


# ============================================================================
# SALARY CAP FIXTURES
# ============================================================================

@pytest.fixture
def cap_calculator(test_db_with_schema):
    """
    Provides CapCalculator instance with test database.
    """
    from salary_cap.cap_calculator import CapCalculator
    return CapCalculator(test_db_with_schema)


@pytest.fixture
def cap_database_api(test_db_with_schema):
    """
    Provides CapDatabaseAPI instance with test database.
    """
    from salary_cap.cap_database_api import CapDatabaseAPI
    return CapDatabaseAPI(test_db_with_schema)


@pytest.fixture
def contract_manager(test_db_with_schema):
    """
    Provides ContractManager instance with test database.
    """
    from salary_cap.contract_manager import ContractManager
    return ContractManager(test_db_with_schema)


@pytest.fixture
def cap_validator(test_db_with_schema):
    """
    Provides CapValidator instance with test database.
    """
    from salary_cap.cap_validator import CapValidator
    return CapValidator(test_db_with_schema)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def test_dynasty_id():
    """Standard dynasty ID for testing."""
    return "test_dynasty"


@pytest.fixture
def test_team_id():
    """Standard team ID for testing (Detroit Lions)."""
    return 7


@pytest.fixture
def test_player_id():
    """Standard player ID for testing."""
    return 12345


@pytest.fixture
def test_season():
    """Standard season year for testing."""
    return 2025


@pytest.fixture
def sample_veteran_contract():
    """
    Sample veteran contract parameters.

    Returns:
        Dict with contract parameters for testing
    """
    return {
        'contract_years': 4,
        'total_value': 40_000_000,
        'signing_bonus': 16_000_000,
        'base_salaries': [1_000_000, 6_000_000, 8_000_000, 9_000_000],
        'guaranteed_amounts': [1_000_000, 6_000_000, 0, 0],
        'contract_type': 'VETERAN'
    }


@pytest.fixture
def sample_rookie_contract():
    """
    Sample rookie contract parameters.

    Returns:
        Dict with contract parameters for testing
    """
    return {
        'contract_years': 4,
        'total_value': 20_000_000,
        'signing_bonus': 10_000_000,
        'base_salaries': [840_000, 2_500_000, 3_330_000, 3_330_000],
        'guaranteed_amounts': [840_000, 2_500_000, 3_330_000, 3_330_000],
        'contract_type': 'ROOKIE'
    }


@pytest.fixture
def initialized_team_cap(cap_database_api, test_team_id, test_season, test_dynasty_id):
    """
    Initialize team salary cap for testing.

    Returns:
        cap_id of initialized team cap
    """
    return cap_database_api.initialize_team_cap(
        team_id=test_team_id,
        season=test_season,
        dynasty_id=test_dynasty_id,
        salary_cap_limit=279_200_000,  # 2025 cap
        carryover_from_previous=0
    )
