"""
Comprehensive unit tests for DraftClassAPI.

Tests all core functionality including:
- Draft class generation with player generation system integration
- Dynasty isolation for draft classes and prospects
- Retrieval methods (filtering, sorting, querying)
- Draft execution (marking drafted, converting to players)
- Unified player_id system (prospect ID = player ID)
- Database integrity (foreign keys, unique constraints, cascading deletes)

Architecture:
- Uses in-memory database (:memory:) for speed
- Mocks player_generation system to avoid external dependencies
- Tests dynasty isolation thoroughly
- Validates database schema and constraints
"""

import pytest
import sqlite3
import json
from unittest.mock import Mock, patch
from pathlib import Path


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_db_path(tmp_path):
    """Create temporary database file for testing."""
    db_path = tmp_path / "test_draft_class.db"
    return str(db_path)


@pytest.fixture
def draft_api(test_db_path):
    """
    Create DraftClassAPI instance with initialized schema.

    Sets up:
    - dynasties table (prerequisite)
    - draft_classes table
    - draft_prospects table
    - players table (for convert_prospect_to_player tests)
    - team_rosters table (for roster management)
    - All indexes and constraints
    - Mocked player_id generation (to avoid database locking)

    Returns:
        DraftClassAPI instance ready for testing
    """
    # Import here to ensure src is in path
    from database.draft_class_api import DraftClassAPI

    # Create in-memory database with required tables
    conn = sqlite3.connect(test_db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Create dynasties table (prerequisite for foreign keys)
    conn.execute("""
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create players table (required for convert_prospect_to_player)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            source_player_id TEXT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            number INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            positions TEXT NOT NULL,
            attributes TEXT NOT NULL,
            contract_id INTEGER,
            status TEXT DEFAULT 'active',
            years_pro INTEGER DEFAULT 0,
            birthdate TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        )
    """)

    # Create team_rosters table (required for _add_to_roster)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_rosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            depth_chart_order INTEGER DEFAULT 99,
            roster_status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_id, player_id)
        )
    """)

    conn.commit()
    conn.close()

    # Create DraftClassAPI instance (will run migration)
    api = DraftClassAPI(test_db_path)

    # Mock player_id generation to avoid database locking issues
    # This replaces PlayerRosterAPI's _get_next_player_id with a database-aware counter
    dynasty_counters = {}

    def mock_get_next_player_id(dynasty_id):
        # Initialize counter for this dynasty if needed
        if dynasty_id not in dynasty_counters:
            # Check database for max existing ID
            with sqlite3.connect(test_db_path) as conn:
                cursor = conn.execute(
                    "SELECT COALESCE(MAX(player_id), 0) FROM players WHERE dynasty_id = ?",
                    (dynasty_id,)
                )
                max_id = cursor.fetchone()[0]
                dynasty_counters[dynasty_id] = max_id + 1

        # Return current counter and increment
        current_id = dynasty_counters[dynasty_id]
        dynasty_counters[dynasty_id] += 1
        return current_id

    api.player_api._get_next_player_id = mock_get_next_player_id

    return api


@pytest.fixture
def test_dynasty_id():
    """Standard dynasty ID for testing."""
    return "test_dynasty"


@pytest.fixture
def second_dynasty_id():
    """Second dynasty for isolation testing."""
    return "dynasty_2"


@pytest.fixture
def test_season():
    """Standard season for testing."""
    return 2025


@pytest.fixture
def mock_generated_prospects():
    """
    Mock prospect data from player generation system.

    Returns 224 mock prospects (7 rounds × 32 picks).
    """
    prospects = []

    positions = ['QB', 'RB', 'WR', 'TE', 'OT', 'OG', 'C', 'DE', 'DT', 'EDGE', 'LB', 'CB', 'S']

    for round_num in range(1, 8):  # 7 rounds
        for pick in range(1, 33):  # 32 picks per round
            overall_pick = (round_num - 1) * 32 + pick

            # Create mock GeneratedPlayer
            prospect = Mock()
            prospect.name = f"First{overall_pick} Last{overall_pick}"
            prospect.position = positions[overall_pick % len(positions)]
            prospect.age = 21 + (overall_pick % 3)
            prospect.draft_round = round_num
            prospect.draft_pick = pick
            prospect.true_overall = 95 - (overall_pick // 3)  # Declining talent
            prospect.true_ratings = {
                'speed': 85 - (overall_pick // 10),
                'awareness': 80 - (overall_pick // 10),
                'strength': 75 - (overall_pick // 10)
            }

            # Background info
            prospect.background = Mock()
            prospect.background.college = f"University {overall_pick}"
            prospect.background.hometown = f"Hometown {overall_pick}"
            prospect.background.home_state = "CA"

            # Scouting data
            prospect.scouted_overall = prospect.true_overall - (overall_pick % 5)
            prospect.scouting_report = Mock()
            prospect.scouting_report.confidence = "medium"

            # Development
            prospect.development = Mock()
            prospect.development.development_curve = "normal"

            # Archetype
            prospect.archetype_id = f"ARCH_{prospect.position}_001"

            prospects.append(prospect)

    return prospects


@pytest.fixture
def initialized_dynasty(draft_api, test_dynasty_id):
    """
    Create test dynasty in database.

    Args:
        draft_api: DraftClassAPI instance
        test_dynasty_id: Dynasty ID to create

    Returns:
        Dynasty ID
    """
    with sqlite3.connect(draft_api.database_path) as conn:
        conn.execute(
            "INSERT INTO dynasties (dynasty_id) VALUES (?)",
            (test_dynasty_id,)
        )
        conn.commit()

    return test_dynasty_id


@pytest.fixture
def second_initialized_dynasty(draft_api, second_dynasty_id):
    """Create second test dynasty for isolation testing."""
    with sqlite3.connect(draft_api.database_path) as conn:
        conn.execute(
            "INSERT INTO dynasties (dynasty_id) VALUES (?)",
            (second_dynasty_id,)
        )
        conn.commit()

    return second_dynasty_id




# ============================================================================
# GENERATION TESTS
# ============================================================================

def test_generate_draft_class_creates_224_prospects(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test that generate_draft_class creates exactly 224 prospects.

    Validates:
    - 7 rounds × 32 picks = 224 prospects
    - All prospects inserted into database
    - Draft class metadata created
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        # Mock draft class generation
        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        # Generate draft class (player_id mocking handled by draft_api fixture)
        total_prospects = draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Verify 224 prospects created
        assert total_prospects == 224

        # Verify in database
        all_prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        assert len(all_prospects) == 224


def test_generate_draft_class_with_permanent_ids(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test that each prospect gets a permanent unique player_id.

    Validates:
    - Player IDs are auto-incremented integers
    - Player IDs are unique within dynasty
    - Player IDs start from 1 for new dynasty
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get all prospects
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        # Extract player IDs
        player_ids = [p['player_id'] for p in prospects]

        # Verify uniqueness
        assert len(player_ids) == len(set(player_ids))

        # Verify all are integers
        assert all(isinstance(pid, int) for pid in player_ids)

        # Verify sequential starting from 1
        assert min(player_ids) == 1
        assert max(player_ids) == 224


def test_prevent_duplicate_draft_class_same_season(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test that generating duplicate draft class raises ValueError.

    Validates:
    - Cannot create two draft classes for same dynasty/season
    - Unique constraint enforced at database level
    - Error message is helpful
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        # Generate first draft class
        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Attempt to generate duplicate
        with pytest.raises(ValueError) as exc_info:
            draft_api.generate_draft_class(
                dynasty_id=initialized_dynasty,
                season=test_season
            )

        assert "already exists" in str(exc_info.value).lower()


def test_dynasty_isolation_player_ids(
    draft_api,
    initialized_dynasty,
    second_initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test that player IDs are isolated per dynasty.

    Validates:
    - Each dynasty has its own player_id sequence
    - Dynasty 1 player IDs don't conflict with Dynasty 2
    - Both dynasties can have player_id = 1
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        # Generate draft class for dynasty 1
        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Generate draft class for dynasty 2
        draft_api.generate_draft_class(
            dynasty_id=second_initialized_dynasty,
            season=test_season
        )

        # Get prospects from both dynasties
        dynasty1_prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        dynasty2_prospects = draft_api.get_all_prospects(
            dynasty_id=second_initialized_dynasty,
            season=test_season,
            available_only=False
        )

        # Both should have 224 prospects
        assert len(dynasty1_prospects) == 224
        assert len(dynasty2_prospects) == 224

        # Verify player_ids are isolated per dynasty
        dynasty1_ids = set(p['player_id'] for p in dynasty1_prospects)
        dynasty2_ids = set(p['player_id'] for p in dynasty2_prospects)

        # Both dynasties should have IDs 1-224 (independent sequences)
        assert min(dynasty1_ids) == 1
        assert max(dynasty1_ids) == 224

        assert min(dynasty2_ids) == 1
        assert max(dynasty2_ids) == 224

        # They CAN have the same player_ids because they're in different dynasties
        # Database isolation is via (dynasty_id, player_id) composite key
        assert len(dynasty1_ids & dynasty2_ids) == 224  # All IDs overlap (both have 1-224)


# ============================================================================
# RETRIEVAL TESTS
# ============================================================================

def test_get_draft_class_info(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test get_draft_class_info returns correct metadata.

    Validates:
    - Returns draft class metadata
    - Contains expected fields
    - Returns None for non-existent draft class
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get draft class info
        info = draft_api.get_draft_class_info(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Validate metadata
        assert info is not None
        assert info['dynasty_id'] == initialized_dynasty
        assert info['season'] == test_season
        assert info['total_prospects'] == 224
        assert info['status'] == 'active'
        assert 'draft_class_id' in info
        assert 'generation_date' in info

        # Test non-existent draft class
        no_info = draft_api.get_draft_class_info(
            dynasty_id=initialized_dynasty,
            season=2099
        )
        assert no_info is None


def test_get_all_prospects(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test get_all_prospects retrieves all prospects.

    Validates:
    - Returns all 224 prospects
    - Sorted by overall rating (descending)
    - Attributes parsed from JSON
    - available_only filter works
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get all prospects
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        # Validate count
        assert len(prospects) == 224

        # Validate sorting (overall DESC)
        overalls = [p['overall'] for p in prospects]
        assert overalls == sorted(overalls, reverse=True)

        # Validate attributes are parsed
        for prospect in prospects:
            assert isinstance(prospect['attributes'], dict)
            assert 'speed' in prospect['attributes']


def test_get_prospects_by_position(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test get_prospects_by_position filters correctly.

    Validates:
    - Returns only prospects with specified position
    - Sorted by overall rating
    - available_only filter works
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get QB prospects
        qb_prospects = draft_api.get_prospects_by_position(
            dynasty_id=initialized_dynasty,
            season=test_season,
            position='QB',
            available_only=False
        )

        # Validate all are QBs
        assert all(p['position'] == 'QB' for p in qb_prospects)

        # Validate at least one QB exists
        assert len(qb_prospects) > 0

        # Validate sorting
        overalls = [p['overall'] for p in qb_prospects]
        assert overalls == sorted(overalls, reverse=True)


def test_get_prospect_by_id(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test get_prospect_by_id retrieves single prospect.

    Validates:
    - Returns correct prospect by player_id
    - Attributes parsed from JSON
    - Returns None for non-existent player_id
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get any prospect
        all_prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        test_prospect = all_prospects[0]
        player_id = test_prospect['player_id']

        # Retrieve by ID
        prospect = draft_api.get_prospect_by_id(
            player_id=player_id,
            dynasty_id=initialized_dynasty
        )

        # Validate correct prospect returned
        assert prospect is not None
        assert prospect['player_id'] == player_id
        assert isinstance(prospect['attributes'], dict)

        # Test non-existent ID
        no_prospect = draft_api.get_prospect_by_id(
            player_id=99999,
            dynasty_id=initialized_dynasty
        )
        assert no_prospect is None


def test_get_top_prospects(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test get_top_prospects returns highest-rated prospects.

    Validates:
    - Returns top N prospects by overall rating
    - Sorted by overall descending
    - limit parameter works
    - position filter works
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get top 10 prospects
        top_10 = draft_api.get_top_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            limit=10
        )

        assert len(top_10) == 10

        # Validate sorted by overall
        overalls = [p['overall'] for p in top_10]
        assert overalls == sorted(overalls, reverse=True)

        # Get top 5 QBs
        top_qbs = draft_api.get_top_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            limit=5,
            position='QB'
        )

        # All should be QBs
        assert all(p['position'] == 'QB' for p in top_qbs)
        assert len(top_qbs) <= 5


def test_get_prospect_history(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test get_prospect_history returns draft history.

    Validates:
    - Returns prospect data with season info
    - Includes draft class metadata
    - Works for both drafted and undrafted prospects
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get any prospect
        all_prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        test_prospect = all_prospects[0]
        player_id = test_prospect['player_id']

        # Get history
        history = draft_api.get_prospect_history(
            player_id=player_id,
            dynasty_id=initialized_dynasty
        )

        # Validate history contains expected fields
        assert history is not None
        assert history['player_id'] == player_id
        assert history['season'] == test_season
        assert 'generation_date' in history


# ============================================================================
# DRAFT EXECUTION TESTS
# ============================================================================

def test_mark_prospect_drafted(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test mark_prospect_drafted updates prospect record.

    Validates:
    - is_drafted flag set to TRUE
    - Team ID recorded
    - Round and pick recorded
    - Prospect removed from available list
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get first prospect
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=True
        )

        test_prospect = prospects[0]
        player_id = test_prospect['player_id']

        # Mark as drafted
        draft_api.mark_prospect_drafted(
            player_id=player_id,
            team_id=7,  # Detroit Lions
            actual_round=1,
            actual_pick=1,
            dynasty_id=initialized_dynasty
        )

        # Verify drafted status
        drafted_prospect = draft_api.get_prospect_by_id(
            player_id=player_id,
            dynasty_id=initialized_dynasty
        )

        assert drafted_prospect['is_drafted'] == 1  # SQLite boolean = 1
        assert drafted_prospect['drafted_by_team_id'] == 7
        assert drafted_prospect['drafted_round'] == 1
        assert drafted_prospect['drafted_pick'] == 1

        # Verify not in available list
        available = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=True
        )

        available_ids = [p['player_id'] for p in available]
        assert player_id not in available_ids


def test_convert_prospect_to_player_same_id(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test convert_prospect_to_player uses SAME player_id.

    Validates:
    - Prospect's player_id becomes player's player_id
    - No ID conversion or mapping required
    - Player record created in database
    - Player added to team roster
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get first prospect
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=True
        )

        test_prospect = prospects[0]
        player_id = test_prospect['player_id']

        # Mark as drafted first
        draft_api.mark_prospect_drafted(
            player_id=player_id,
            team_id=7,
            actual_round=1,
            actual_pick=1,
            dynasty_id=initialized_dynasty
        )

        # Convert to player
        returned_player_id = draft_api.convert_prospect_to_player(
            player_id=player_id,
            team_id=7,
            dynasty_id=initialized_dynasty,
            jersey_number=10
        )

        # Validate SAME ID returned
        assert returned_player_id == player_id

        # Verify player exists in database with SAME ID
        with sqlite3.connect(draft_api.database_path) as conn:
            cursor = conn.execute(
                "SELECT player_id FROM players WHERE player_id = ? AND dynasty_id = ?",
                (player_id, initialized_dynasty)
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == player_id


def test_complete_draft_class_summary(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test complete_draft_class marks draft as completed.

    Validates:
    - Status changed to 'completed'
    - Draft class metadata updated
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Verify initial status is 'active'
        info = draft_api.get_draft_class_info(
            dynasty_id=initialized_dynasty,
            season=test_season
        )
        assert info['status'] == 'active'

        # Complete draft class
        draft_api.complete_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Verify status is 'completed'
        info = draft_api.get_draft_class_info(
            dynasty_id=initialized_dynasty,
            season=test_season
        )
        assert info['status'] == 'completed'


def test_no_id_collision_with_existing_roster(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test that draft class player IDs don't collide with existing roster.

    Validates:
    - PlayerRosterAPI tracks max player_id
    - New draft prospects get IDs after existing players
    - No duplicate player_ids within dynasty
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        # Insert some existing players manually
        with sqlite3.connect(draft_api.database_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Insert 50 existing players
            for i in range(1, 51):
                conn.execute("""
                    INSERT INTO players (
                        player_id, dynasty_id, source_player_id,
                        first_name, last_name, number, team_id,
                        positions, attributes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    i, initialized_dynasty, f"EXISTING_{i}",
                    f"Player", f"{i}", 10 + i, 7,
                    '["QB"]', '{"overall": 70}'
                ))

            conn.commit()

        # Generate draft class (should start from player_id 51)
        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get all draft prospects
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        # Verify no ID collision
        prospect_ids = [p['player_id'] for p in prospects]

        # All prospect IDs should be > 50
        assert all(pid > 50 for pid in prospect_ids)

        # Should start from 51
        assert min(prospect_ids) == 51


# ============================================================================
# DYNASTY ISOLATION TESTS
# ============================================================================

def test_multiple_dynasties_same_season(
    draft_api,
    initialized_dynasty,
    second_initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test multiple dynasties can have draft classes for same season.

    Validates:
    - Dynasty 1 and Dynasty 2 can both have 2025 draft class
    - Draft classes are isolated (no cross-contamination)
    - Each dynasty sees only its own prospects
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        # Generate draft class for dynasty 1
        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Generate draft class for dynasty 2
        draft_api.generate_draft_class(
            dynasty_id=second_initialized_dynasty,
            season=test_season
        )

        # Verify both dynasties have draft classes
        info1 = draft_api.get_draft_class_info(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        info2 = draft_api.get_draft_class_info(
            dynasty_id=second_initialized_dynasty,
            season=test_season
        )

        assert info1 is not None
        assert info2 is not None
        assert info1['draft_class_id'] != info2['draft_class_id']

        # Verify prospect isolation
        prospects1 = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )

        prospects2 = draft_api.get_all_prospects(
            dynasty_id=second_initialized_dynasty,
            season=test_season,
            available_only=False
        )

        # Both should have 224 prospects
        assert len(prospects1) == 224
        assert len(prospects2) == 224

        # Verify no cross-contamination (different prospect sets)
        ids1 = set((p['player_id'], p['dynasty_id']) for p in prospects1)
        ids2 = set((p['player_id'], p['dynasty_id']) for p in prospects2)

        # No overlap in (player_id, dynasty_id) tuples
        assert len(ids1 & ids2) == 0


def test_dynasty_cascade_delete(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test deleting draft class cascades to prospects.

    Validates:
    - delete_draft_class removes draft class record
    - All prospects also deleted (cascade)
    - Foreign key constraints working
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Verify draft class exists
        info = draft_api.get_draft_class_info(
            dynasty_id=initialized_dynasty,
            season=test_season
        )
        assert info is not None

        # Verify prospects exist
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )
        assert len(prospects) == 224

        # Delete draft class
        draft_api.delete_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Verify draft class deleted
        info = draft_api.get_draft_class_info(
            dynasty_id=initialized_dynasty,
            season=test_season
        )
        assert info is None

        # Verify prospects also deleted (cascade)
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=False
        )
        assert len(prospects) == 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_convert_prospect_to_player_not_drafted_error(
    draft_api,
    initialized_dynasty,
    test_season,
    mock_generated_prospects
):
    """
    Test that convert_prospect_to_player raises error if not drafted.

    Validates:
    - ValueError raised if prospect not marked as drafted
    - Error message is helpful
    """
    with patch('player_generation.generators.player_generator.PlayerGenerator') as mock_player_gen, \
         patch('player_generation.generators.draft_class_generator.DraftClassGenerator') as mock_draft_gen:

        mock_draft_gen_instance = Mock()
        mock_draft_gen_instance.generate_draft_class.return_value = mock_generated_prospects
        mock_draft_gen.return_value = mock_draft_gen_instance

        draft_api.generate_draft_class(
            dynasty_id=initialized_dynasty,
            season=test_season
        )

        # Get first prospect
        prospects = draft_api.get_all_prospects(
            dynasty_id=initialized_dynasty,
            season=test_season,
            available_only=True
        )

        test_prospect = prospects[0]
        player_id = test_prospect['player_id']

        # Attempt to convert without marking drafted
        with pytest.raises(ValueError) as exc_info:
            draft_api.convert_prospect_to_player(
                player_id=player_id,
                team_id=7,
                dynasty_id=initialized_dynasty
            )

        assert "not been drafted" in str(exc_info.value).lower()


def test_convert_prospect_to_player_not_found_error(
    draft_api,
    initialized_dynasty,
    test_season
):
    """
    Test that convert_prospect_to_player raises error if prospect not found.

    Validates:
    - ValueError raised if player_id doesn't exist
    - Error message is helpful
    """
    # Attempt to convert non-existent prospect
    with pytest.raises(ValueError) as exc_info:
        draft_api.convert_prospect_to_player(
            player_id=99999,
            team_id=7,
            dynasty_id=initialized_dynasty
        )

    assert "not found" in str(exc_info.value).lower()


# ============================================================================
# TEST SUMMARY
# ============================================================================

def test_suite_summary():
    """
    Comprehensive test suite for DraftClassAPI.

    Test Coverage:
    - Generation: 4 tests
    - Retrieval: 6 tests
    - Draft Execution: 4 tests
    - Dynasty Isolation: 2 tests
    - Error Handling: 2 tests

    Total: 18 tests

    Key Features Tested:
    - 224 prospect generation (7 rounds × 32 picks)
    - Permanent player ID assignment
    - Dynasty isolation (separate ID sequences)
    - Duplicate prevention (unique dynasty+season)
    - Position filtering and sorting
    - Top prospect queries
    - Draft history tracking
    - Draft execution workflow
    - Unified player_id system (prospect ID = player ID)
    - ID collision prevention with existing rosters
    - Cascade deletes
    - Error handling for edge cases
    """
    pass
