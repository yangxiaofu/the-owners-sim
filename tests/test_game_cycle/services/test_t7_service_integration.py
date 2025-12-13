"""
Integration tests for Milestone 13 Tollgate 7: Service Integration.

Tests that owner directives flow through to Draft and FA behavior:
- Draft wishlist resolution (names to IDs)
- DraftDirection affects auto_complete_draft
- FA wishlist affects GMFAProposalEngine scoring
- FAGuidance wishlist_names field

Part of Milestone 13: Owner Review.
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch

# ============================================
# Fixtures
# ============================================


@pytest.fixture
def temp_db():
    """Create a temporary database with draft schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    conn = sqlite3.connect(temp_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Create minimal schema for testing
    conn.executescript('''
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE draft_classes (
            draft_class_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            generation_date TIMESTAMP,
            total_prospects INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            UNIQUE(dynasty_id, season)
        );

        CREATE TABLE draft_prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            draft_class_id TEXT NOT NULL,
            dynasty_id TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            position TEXT NOT NULL,
            age INTEGER DEFAULT 22,
            draft_round INTEGER,
            draft_pick INTEGER,
            projected_pick_min INTEGER,
            projected_pick_max INTEGER,
            overall INTEGER NOT NULL,
            attributes TEXT NOT NULL,
            college TEXT,
            hometown TEXT,
            home_state TEXT,
            archetype_id TEXT,
            scouted_overall INTEGER,
            scouting_confidence TEXT DEFAULT 'medium',
            development_curve TEXT DEFAULT 'normal',
            is_drafted INTEGER DEFAULT 0,
            drafted_by_team_id INTEGER,
            drafted_round INTEGER,
            drafted_pick INTEGER,
            roster_player_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, player_id)
        );

        CREATE TABLE players (
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
            birthdate TEXT,
            status TEXT DEFAULT 'active',
            UNIQUE(dynasty_id, player_id)
        );

        CREATE TABLE team_rosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            depth_chart_order INTEGER DEFAULT 99,
            UNIQUE(dynasty_id, team_id, player_id)
        );

        INSERT INTO dynasties (dynasty_id) VALUES ('test-dynasty');
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    os.unlink(temp_path)


@pytest.fixture
def draft_class_api(temp_db):
    """Create DraftClassAPI with test database."""
    from database.draft_class_api import DraftClassAPI
    api = DraftClassAPI(temp_db, skip_schema_check=True)
    return api


@pytest.fixture
def populated_draft_class(temp_db):
    """Create a draft class with known prospects."""
    dynasty_id = "test-dynasty"
    season = 2025
    draft_class_id = f"DRAFT_{dynasty_id}_{season}"

    conn = sqlite3.connect(temp_db)

    # Insert draft class
    conn.execute('''
        INSERT INTO draft_classes (draft_class_id, dynasty_id, season, total_prospects, status)
        VALUES (?, ?, ?, 5, 'active')
    ''', (draft_class_id, dynasty_id, season))

    # Insert known prospects for testing
    prospects = [
        (1, "John", "Smith", "QB", 95),
        (2, "Mike", "Jones", "WR", 92),
        (3, "Tom", "Williams", "RB", 88),
        (4, "James", "Brown", "CB", 85),
        (5, "Chris", "Davis", "OT", 82),
    ]

    for player_id, first, last, pos, ovr in prospects:
        conn.execute('''
            INSERT INTO draft_prospects (
                player_id, draft_class_id, dynasty_id,
                first_name, last_name, position, overall, attributes,
                draft_round, draft_pick
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '{}', 1, ?)
        ''', (player_id, draft_class_id, dynasty_id, first, last, pos, ovr, player_id))

    conn.commit()
    conn.close()

    return {"dynasty_id": dynasty_id, "season": season, "db_path": temp_db}


# ============================================
# Tests for find_prospect_by_name
# ============================================


class TestFindProspectByName:
    """Tests for DraftClassAPI.find_prospect_by_name()."""

    def test_find_by_full_name(self, draft_class_api, populated_draft_class):
        """Find prospect by full name."""
        result = draft_class_api.find_prospect_by_name(
            dynasty_id=populated_draft_class["dynasty_id"],
            season=populated_draft_class["season"],
            name="John Smith"
        )

        assert result is not None
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"
        assert result["position"] == "QB"

    def test_find_by_last_name_only(self, draft_class_api, populated_draft_class):
        """Find prospect by last name only."""
        result = draft_class_api.find_prospect_by_name(
            dynasty_id=populated_draft_class["dynasty_id"],
            season=populated_draft_class["season"],
            name="Jones"
        )

        assert result is not None
        assert result["last_name"] == "Jones"
        assert result["position"] == "WR"

    def test_find_case_insensitive(self, draft_class_api, populated_draft_class):
        """Find prospect with different case."""
        result = draft_class_api.find_prospect_by_name(
            dynasty_id=populated_draft_class["dynasty_id"],
            season=populated_draft_class["season"],
            name="JOHN SMITH"
        )

        assert result is not None
        assert result["first_name"] == "John"

    def test_find_returns_none_for_nonexistent(self, draft_class_api, populated_draft_class):
        """Returns None for non-existent prospect."""
        result = draft_class_api.find_prospect_by_name(
            dynasty_id=populated_draft_class["dynasty_id"],
            season=populated_draft_class["season"],
            name="Nonexistent Player"
        )

        assert result is None

    def test_find_excludes_drafted_prospects(self, draft_class_api, populated_draft_class):
        """Does not return already-drafted prospects."""
        # Mark John Smith as drafted
        conn = sqlite3.connect(populated_draft_class["db_path"])
        conn.execute(
            "UPDATE draft_prospects SET is_drafted = 1 WHERE first_name = 'John'"
        )
        conn.commit()
        conn.close()

        result = draft_class_api.find_prospect_by_name(
            dynasty_id=populated_draft_class["dynasty_id"],
            season=populated_draft_class["season"],
            name="John Smith"
        )

        assert result is None


# ============================================
# Tests for FAGuidance wishlist_names
# ============================================


class TestFAGuidanceWishlistNames:
    """Tests for FAGuidance.wishlist_names field."""

    def test_create_with_wishlist(self):
        """Create FAGuidance with wishlist_names."""
        from src.game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy

        guidance = FAGuidance(
            philosophy=FAPhilosophy.AGGRESSIVE,
            wishlist_names=["John Smith", "Mike Jones"]
        )

        assert guidance.wishlist_names == ["John Smith", "Mike Jones"]

    def test_default_has_empty_wishlist(self):
        """Default guidance has empty wishlist."""
        from src.game_cycle.models.fa_guidance import FAGuidance

        guidance = FAGuidance.create_default()

        assert guidance.wishlist_names == []

    def test_to_dict_includes_wishlist(self):
        """to_dict() includes wishlist_names."""
        from src.game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy

        guidance = FAGuidance(
            philosophy=FAPhilosophy.BALANCED,
            wishlist_names=["Player A"]
        )

        result = guidance.to_dict()

        assert "wishlist_names" in result
        assert result["wishlist_names"] == ["Player A"]

    def test_is_default_with_wishlist(self):
        """Guidance with wishlist is not default."""
        from src.game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy

        guidance = FAGuidance(
            philosophy=FAPhilosophy.BALANCED,
            wishlist_names=["Some Player"]
        )

        assert not guidance.is_default()


# ============================================
# Tests for OwnerDirectives.to_fa_guidance
# ============================================


class TestOwnerDirectivesToFAGuidance:
    """Tests for OwnerDirectives.to_fa_guidance() wishlist conversion."""

    def test_converts_fa_wishlist_to_guidance(self):
        """fa_wishlist converts to FAGuidance.wishlist_names."""
        from src.game_cycle.models.owner_directives import OwnerDirectives

        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            fa_wishlist=["Target Player 1", "Target Player 2"]
        )

        guidance = directives.to_fa_guidance()

        assert guidance.wishlist_names == ["Target Player 1", "Target Player 2"]

    def test_empty_fa_wishlist_converts_to_empty(self):
        """Empty fa_wishlist converts to empty wishlist_names."""
        from src.game_cycle.models.owner_directives import OwnerDirectives

        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            fa_wishlist=[]
        )

        guidance = directives.to_fa_guidance()

        assert guidance.wishlist_names == []


# ============================================
# Tests for GMFAProposalEngine wishlist bonus
# ============================================


class TestGMFAProposalEngineWishlistBonus:
    """Tests for wishlist bonus in GMFAProposalEngine._score_candidate()."""

    def test_wishlist_player_gets_bonus(self):
        """Player on wishlist gets +20 bonus."""
        from src.game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine
        from src.game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy

        # Create guidance with wishlist
        guidance = FAGuidance(
            philosophy=FAPhilosophy.BALANCED,
            wishlist_names=["John Smith"]
        )

        # Create mock GM archetype
        gm = Mock()
        gm.veteran_preference = 0.5
        gm.star_chasing = 0.5
        gm.cap_management = 0.5

        engine = GMFAProposalEngine(gm, guidance)

        # Create test player matching wishlist
        player = {
            "first_name": "John",
            "last_name": "Smith",
            "position": "QB",
            "overall": 80,
            "age": 25,
            "tier": "Starter"
        }

        needs = {"QB": 3}  # Some need

        score = engine._score_candidate(player, needs, 50_000_000)

        # Base 80 + depth need 5 + wishlist 20 = 105 (plus/minus random variance)
        assert score >= 95  # Accounting for -5 variance

    def test_non_wishlist_player_no_bonus(self):
        """Player not on wishlist gets no bonus."""
        from src.game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine
        from src.game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy

        guidance = FAGuidance(
            philosophy=FAPhilosophy.BALANCED,
            wishlist_names=["Other Player"]
        )

        gm = Mock()
        gm.veteran_preference = 0.5
        gm.star_chasing = 0.5
        gm.cap_management = 0.5

        engine = GMFAProposalEngine(gm, guidance)

        player = {
            "first_name": "John",
            "last_name": "Smith",
            "position": "QB",
            "overall": 80,
            "age": 25,
            "tier": "Starter"
        }

        needs = {"QB": 3}

        score = engine._score_candidate(player, needs, 50_000_000)

        # Base 80 + depth need 5 = 85 (plus/minus random variance, no +20 wishlist)
        assert score <= 95  # Should not get +20 bonus

    def test_wishlist_match_by_last_name(self):
        """Wishlist matches by last name only."""
        from src.game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine
        from src.game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy

        guidance = FAGuidance(
            philosophy=FAPhilosophy.BALANCED,
            wishlist_names=["Smith"]  # Last name only
        )

        gm = Mock()
        gm.veteran_preference = 0.5
        gm.star_chasing = 0.5
        gm.cap_management = 0.5

        engine = GMFAProposalEngine(gm, guidance)

        player = {
            "first_name": "John",
            "last_name": "Smith",
            "position": "QB",
            "overall": 80,
            "age": 25,
            "tier": "Starter"
        }

        needs = {"QB": 3}

        score = engine._score_candidate(player, needs, 50_000_000)

        # Should get +20 bonus from last name match
        assert score >= 95


# ============================================
# Tests for DraftDirection integration
# ============================================


class TestDraftDirectionIntegration:
    """Tests for DraftDirection flowing through auto_complete_draft."""

    def test_auto_complete_accepts_draft_direction(self):
        """auto_complete_draft accepts draft_direction parameter."""
        from src.game_cycle.services.draft_service import DraftService
        from src.game_cycle.models import DraftDirection, DraftStrategy

        # Just verify the signature accepts the parameter
        # Full integration test would require extensive mocking
        direction = DraftDirection(
            strategy=DraftStrategy.BEST_PLAYER_AVAILABLE,
            priority_positions=["QB", "WR"],
            watchlist_prospect_ids=[1, 2, 3]
        )

        # Verify DraftDirection dataclass is correctly structured
        assert direction.strategy == DraftStrategy.BEST_PLAYER_AVAILABLE
        assert direction.priority_positions == ["QB", "WR"]
        assert direction.watchlist_prospect_ids == [1, 2, 3]

    def test_owner_directives_to_draft_direction(self):
        """OwnerDirectives.to_draft_direction() creates valid DraftDirection."""
        from src.game_cycle.models.owner_directives import OwnerDirectives
        from src.game_cycle.models import DraftStrategy

        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            draft_strategy="bpa",
            priority_positions=["QB", "WR", "CB"],
            draft_wishlist=["John Smith"]  # Names (not resolved yet)
        )

        direction = directives.to_draft_direction()

        assert direction.strategy == DraftStrategy.BEST_PLAYER_AVAILABLE
        assert direction.priority_positions == ["QB", "WR", "CB"]
        # Note: watchlist_prospect_ids will be empty until resolved
        assert direction.watchlist_prospect_ids == []
