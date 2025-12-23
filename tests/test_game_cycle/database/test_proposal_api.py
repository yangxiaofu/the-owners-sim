"""
Unit tests for ProposalAPI.

Part of Tollgate 3: GM Proposal System persistence layer.
"""
import json
import pytest
import sqlite3
import tempfile
import os
from datetime import datetime

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.proposal_api import ProposalAPI
from src.game_cycle.models.proposal_enums import ProposalType, ProposalStatus
from src.game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_signing_details,
    create_trade_details,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS gm_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT UNIQUE NOT NULL,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            season INTEGER NOT NULL,
            stage TEXT NOT NULL,
            proposal_type TEXT NOT NULL CHECK(proposal_type IN (
                'FRANCHISE_TAG', 'EXTENSION', 'SIGNING', 'TRADE',
                'DRAFT_PICK', 'CUT', 'WAIVER_CLAIM'
            )),
            subject_player_id TEXT,
            details TEXT NOT NULL,
            gm_reasoning TEXT NOT NULL,
            confidence REAL DEFAULT 0.5 CHECK(confidence >= 0 AND confidence <= 1),
            priority INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PENDING' CHECK(status IN (
                'PENDING', 'APPROVED', 'REJECTED', 'MODIFIED', 'EXPIRED'
            )),
            owner_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_id, proposal_id)
        );

        CREATE INDEX IF NOT EXISTS idx_gm_proposals_dynasty_status
            ON gm_proposals(dynasty_id, team_id, status);
        CREATE INDEX IF NOT EXISTS idx_gm_proposals_stage
            ON gm_proposals(dynasty_id, team_id, stage, status);

        -- Insert test dynasties
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other-dynasty', 'Other Dynasty', 2);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def db(db_path):
    """Create a GameCycleDatabase instance."""
    return GameCycleDatabase(db_path)


@pytest.fixture
def api(db):
    """Create a ProposalAPI instance."""
    return ProposalAPI(db)


@pytest.fixture
def dynasty_id():
    """Standard test dynasty ID."""
    return 'test-dynasty'


@pytest.fixture
def team_id():
    """Standard test team ID."""
    return 1


@pytest.fixture
def season():
    """Standard test season."""
    return 2025


@pytest.fixture
def sample_proposal(dynasty_id, team_id, season):
    """Create a sample signing proposal."""
    return PersistentGMProposal(
        dynasty_id=dynasty_id,
        team_id=team_id,
        season=season,
        stage="OFFSEASON_FREE_AGENCY",
        proposal_type=ProposalType.SIGNING,
        details=create_signing_details(
            player_name="John Smith",
            position="WR",
            age=26,
            overall_rating=85,
            contract={"years": 3, "total": 45000000, "guaranteed": 30000000, "aav": 15000000},
            cap_space_before=50000000,
            cap_space_after=35000000,
            competing_offers=2,
        ),
        gm_reasoning="Elite WR fits our offense and addresses priority need.",
        confidence=0.85,
        priority=10,
        subject_player_id="player_123",
    )


# ============================================
# Tests for create_proposal
# ============================================

class TestCreateProposal:
    """Tests for create_proposal method."""

    def test_create_returns_proposal_id(self, api, sample_proposal):
        """Creating a proposal should return the proposal_id."""
        proposal_id = api.create_proposal(sample_proposal)
        assert proposal_id == sample_proposal.proposal_id

    def test_create_persists_proposal(self, api, dynasty_id, team_id, sample_proposal):
        """Created proposal should be retrievable."""
        proposal_id = api.create_proposal(sample_proposal)

        result = api.get_proposal(dynasty_id, team_id, proposal_id)
        assert result is not None
        assert result.proposal_type == ProposalType.SIGNING
        assert result.gm_reasoning == "Elite WR fits our offense and addresses priority need."

    def test_create_sets_created_at(self, api, dynasty_id, team_id, sample_proposal):
        """Created proposal should have created_at timestamp."""
        sample_proposal.created_at = None
        api.create_proposal(sample_proposal)

        result = api.get_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert result.created_at is not None

    def test_create_serializes_details(self, api, db, dynasty_id, team_id, sample_proposal):
        """Details should be serialized as JSON."""
        api.create_proposal(sample_proposal)

        row = db.query_one(
            "SELECT details FROM gm_proposals WHERE proposal_id = ?",
            (sample_proposal.proposal_id,)
        )
        assert row is not None
        details = json.loads(row['details'])
        assert details['player_name'] == "John Smith"
        assert details['contract']['aav'] == 15000000

    def test_create_batch(self, api, dynasty_id, team_id, season):
        """Creating batch of proposals should return all proposal IDs."""
        proposals = [
            PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"player_name": f"Player {i}"},
                gm_reasoning=f"Reason {i}",
            )
            for i in range(3)
        ]

        proposal_ids = api.create_proposals_batch(proposals)
        assert len(proposal_ids) == 3

        # Verify all created
        for pid in proposal_ids:
            result = api.get_proposal(dynasty_id, team_id, pid)
            assert result is not None


# ============================================
# Tests for get_proposal
# ============================================

class TestGetProposal:
    """Tests for get_proposal method."""

    def test_get_returns_none_for_missing(self, api, dynasty_id, team_id):
        """Getting non-existent proposal should return None."""
        result = api.get_proposal(dynasty_id, team_id, "nonexistent-id")
        assert result is None

    def test_get_deserializes_enums(self, api, dynasty_id, team_id, sample_proposal):
        """Get should deserialize enum fields correctly."""
        api.create_proposal(sample_proposal)

        result = api.get_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert isinstance(result.proposal_type, ProposalType)
        assert isinstance(result.status, ProposalStatus)
        assert result.proposal_type == ProposalType.SIGNING
        assert result.status == ProposalStatus.PENDING

    def test_get_deserializes_details(self, api, dynasty_id, team_id, sample_proposal):
        """Get should deserialize JSON details correctly."""
        api.create_proposal(sample_proposal)

        result = api.get_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert isinstance(result.details, dict)
        assert result.details['player_name'] == "John Smith"
        assert result.details['age'] == 26


# ============================================
# Tests for get_pending_proposals
# ============================================

class TestGetPendingProposals:
    """Tests for get_pending_proposals method."""

    def test_get_pending_returns_empty_list(self, api, dynasty_id, team_id):
        """No pending proposals should return empty list."""
        result = api.get_pending_proposals(dynasty_id, team_id)
        assert result == []

    def test_get_pending_returns_only_pending(self, api, dynasty_id, team_id, season):
        """Should only return proposals with PENDING status."""
        # Create pending proposal
        pending = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"player_name": "Pending Player"},
            gm_reasoning="Pending",
        )
        api.create_proposal(pending)

        # Create approved proposal
        approved = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"player_name": "Approved Player"},
            gm_reasoning="Approved",
            status=ProposalStatus.APPROVED,
        )
        api.create_proposal(approved)

        result = api.get_pending_proposals(dynasty_id, team_id)
        assert len(result) == 1
        assert result[0].details['player_name'] == "Pending Player"

    def test_get_pending_filters_by_stage(self, api, dynasty_id, team_id, season):
        """Should filter by stage when provided."""
        # Create FA proposal
        fa_proposal = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"player_name": "FA Player"},
            gm_reasoning="FA",
        )
        api.create_proposal(fa_proposal)

        # Create draft proposal
        draft_proposal = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_DRAFT",
            proposal_type=ProposalType.DRAFT_PICK,
            details={"player_name": "Draft Prospect"},
            gm_reasoning="Draft",
        )
        api.create_proposal(draft_proposal)

        # Get FA proposals only
        result = api.get_pending_proposals(dynasty_id, team_id, stage="OFFSEASON_FREE_AGENCY")
        assert len(result) == 1
        assert result[0].stage == "OFFSEASON_FREE_AGENCY"

    def test_get_pending_ordered_by_priority(self, api, dynasty_id, team_id, season):
        """Pending proposals should be ordered by priority DESC."""
        for priority in [5, 10, 3]:
            p = PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"priority": priority},
                gm_reasoning=f"Priority {priority}",
                priority=priority,
            )
            api.create_proposal(p)

        result = api.get_pending_proposals(dynasty_id, team_id)
        priorities = [r.priority for r in result]
        assert priorities == [10, 5, 3]


# ============================================
# Tests for update_status
# ============================================

class TestUpdateStatus:
    """Tests for update_status method."""

    def test_approve_updates_status(self, api, dynasty_id, team_id, sample_proposal):
        """Approving should set status to APPROVED."""
        api.create_proposal(sample_proposal)

        result = api.approve_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert result is True

        proposal = api.get_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert proposal.status == ProposalStatus.APPROVED
        assert proposal.resolved_at is not None

    def test_reject_updates_status_with_notes(self, api, dynasty_id, team_id, sample_proposal):
        """Rejecting should set status and capture notes."""
        api.create_proposal(sample_proposal)

        result = api.reject_proposal(
            dynasty_id, team_id, sample_proposal.proposal_id,
            notes="Too expensive"
        )
        assert result is True

        proposal = api.get_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert proposal.status == ProposalStatus.REJECTED
        assert proposal.owner_notes == "Too expensive"

    def test_update_returns_false_for_missing(self, api, dynasty_id, team_id):
        """Updating non-existent proposal should return False."""
        result = api.approve_proposal(dynasty_id, team_id, "nonexistent")
        assert result is False


# ============================================
# Tests for expire_pending_proposals
# ============================================

class TestExpirePendingProposals:
    """Tests for expire_pending_proposals method."""

    def test_expire_marks_pending_as_expired(self, api, dynasty_id, team_id, season):
        """All pending proposals for stage should be expired."""
        for i in range(3):
            p = PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"player_name": f"Player {i}"},
                gm_reasoning=f"Reason {i}",
            )
            api.create_proposal(p)

        expired_count = api.expire_pending_proposals(dynasty_id, team_id, "OFFSEASON_FREE_AGENCY")
        assert expired_count == 3

        # Verify all expired
        pending = api.get_pending_proposals(dynasty_id, team_id, stage="OFFSEASON_FREE_AGENCY")
        assert len(pending) == 0

        expired = api.get_proposals_by_status(dynasty_id, team_id, ProposalStatus.EXPIRED)
        assert len(expired) == 3

    def test_expire_does_not_affect_other_stages(self, api, dynasty_id, team_id, season):
        """Expiring one stage should not affect other stages."""
        # FA proposal
        fa = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"player_name": "FA"},
            gm_reasoning="FA",
        )
        api.create_proposal(fa)

        # Draft proposal
        draft = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_DRAFT",
            proposal_type=ProposalType.DRAFT_PICK,
            details={"player_name": "Draft"},
            gm_reasoning="Draft",
        )
        api.create_proposal(draft)

        # Expire FA only
        api.expire_pending_proposals(dynasty_id, team_id, "OFFSEASON_FREE_AGENCY")

        # Draft should still be pending
        pending = api.get_pending_proposals(dynasty_id, team_id, stage="OFFSEASON_DRAFT")
        assert len(pending) == 1


# ============================================
# Tests for approve_all_pending (Trust GM)
# ============================================

class TestApproveAllPending:
    """Tests for approve_all_pending method (Trust GM mode)."""

    def test_approve_all_approves_all_pending(self, api, dynasty_id, team_id, season):
        """All pending proposals should be approved."""
        for i in range(5):
            p = PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"player_name": f"Player {i}"},
                gm_reasoning=f"Reason {i}",
            )
            api.create_proposal(p)

        approved_count = api.approve_all_pending(dynasty_id, team_id)
        assert approved_count == 5

        approved = api.get_proposals_by_status(dynasty_id, team_id, ProposalStatus.APPROVED)
        assert len(approved) == 5
        assert all("Auto-approved" in p.owner_notes for p in approved)

    def test_approve_all_filters_by_stage(self, api, dynasty_id, team_id, season):
        """Should only approve for specified stage."""
        # FA proposals
        for i in range(2):
            p = PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"player_name": f"FA {i}"},
                gm_reasoning="FA",
            )
            api.create_proposal(p)

        # Draft proposal
        draft = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_DRAFT",
            proposal_type=ProposalType.DRAFT_PICK,
            details={"player_name": "Draft"},
            gm_reasoning="Draft",
        )
        api.create_proposal(draft)

        # Approve FA only
        approved_count = api.approve_all_pending(dynasty_id, team_id, stage="OFFSEASON_FREE_AGENCY")
        assert approved_count == 2

        # Draft should still be pending
        pending = api.get_pending_proposals(dynasty_id, team_id)
        assert len(pending) == 1
        assert pending[0].stage == "OFFSEASON_DRAFT"


# ============================================
# Tests for get_proposal_history
# ============================================

class TestGetProposalHistory:
    """Tests for get_proposal_history method."""

    def test_history_returns_all_for_season(self, api, dynasty_id, team_id, season):
        """Should return all proposals for season regardless of status."""
        # Create proposals with different statuses
        pending = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"status": "pending"},
            gm_reasoning="Pending",
        )
        api.create_proposal(pending)

        approved = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"status": "approved"},
            gm_reasoning="Approved",
            status=ProposalStatus.APPROVED,
        )
        api.create_proposal(approved)

        rejected = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"status": "rejected"},
            gm_reasoning="Rejected",
            status=ProposalStatus.REJECTED,
        )
        api.create_proposal(rejected)

        history = api.get_proposal_history(dynasty_id, team_id, season)
        assert len(history) == 3


# ============================================
# Tests for dynasty isolation
# ============================================

class TestDynastyIsolation:
    """Tests for dynasty isolation pattern."""

    def test_proposals_isolated_by_dynasty(self, api, team_id, season):
        """Proposals for different dynasties should be isolated."""
        # Proposal for test-dynasty
        p1 = PersistentGMProposal(
            dynasty_id="test-dynasty",
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"dynasty": "test"},
            gm_reasoning="Test",
        )
        api.create_proposal(p1)

        # Proposal for other-dynasty
        p2 = PersistentGMProposal(
            dynasty_id="other-dynasty",
            team_id=team_id,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"dynasty": "other"},
            gm_reasoning="Other",
        )
        api.create_proposal(p2)

        # Verify isolation
        result1 = api.get_pending_proposals("test-dynasty", team_id)
        result2 = api.get_pending_proposals("other-dynasty", team_id)
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0].details['dynasty'] == "test"
        assert result2[0].details['dynasty'] == "other"

    def test_proposals_isolated_by_team(self, api, dynasty_id, season):
        """Proposals for different teams should be isolated."""
        p1 = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=1,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"team": "1"},
            gm_reasoning="Team 1",
        )
        api.create_proposal(p1)

        p2 = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=2,
            season=season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            details={"team": "2"},
            gm_reasoning="Team 2",
        )
        api.create_proposal(p2)

        result1 = api.get_pending_proposals(dynasty_id, 1)
        result2 = api.get_pending_proposals(dynasty_id, 2)
        assert len(result1) == 1
        assert len(result2) == 1


# ============================================
# Tests for count_pending_proposals
# ============================================

class TestCountPendingProposals:
    """Tests for count_pending_proposals method."""

    def test_count_returns_correct_count(self, api, dynasty_id, team_id, season):
        """Should return correct count of pending proposals."""
        for i in range(4):
            p = PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"i": i},
                gm_reasoning=f"Reason {i}",
            )
            api.create_proposal(p)

        count = api.count_pending_proposals(dynasty_id, team_id)
        assert count == 4

    def test_count_filters_by_stage(self, api, dynasty_id, team_id, season):
        """Should filter count by stage."""
        # 2 FA proposals
        for i in range(2):
            p = PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"i": i},
                gm_reasoning="FA",
            )
            api.create_proposal(p)

        # 1 draft proposal
        p = PersistentGMProposal(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            stage="OFFSEASON_DRAFT",
            proposal_type=ProposalType.DRAFT_PICK,
            details={},
            gm_reasoning="Draft",
        )
        api.create_proposal(p)

        fa_count = api.count_pending_proposals(dynasty_id, team_id, stage="OFFSEASON_FREE_AGENCY")
        draft_count = api.count_pending_proposals(dynasty_id, team_id, stage="OFFSEASON_DRAFT")
        total_count = api.count_pending_proposals(dynasty_id, team_id)

        assert fa_count == 2
        assert draft_count == 1
        assert total_count == 3


# ============================================
# Tests for delete operations
# ============================================

class TestDeleteOperations:
    """Tests for delete operations."""

    def test_delete_proposal(self, api, dynasty_id, team_id, sample_proposal):
        """Should delete a specific proposal."""
        api.create_proposal(sample_proposal)

        deleted = api.delete_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert deleted is True

        result = api.get_proposal(dynasty_id, team_id, sample_proposal.proposal_id)
        assert result is None

    def test_delete_returns_false_for_missing(self, api, dynasty_id, team_id):
        """Should return False for non-existent proposal."""
        deleted = api.delete_proposal(dynasty_id, team_id, "nonexistent")
        assert deleted is False

    def test_delete_proposals_for_season(self, api, dynasty_id, team_id, season):
        """Should delete all proposals for a season."""
        for i in range(5):
            p = PersistentGMProposal(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                stage="OFFSEASON_FREE_AGENCY",
                proposal_type=ProposalType.SIGNING,
                details={"i": i},
                gm_reasoning=f"Reason {i}",
            )
            api.create_proposal(p)

        deleted_count = api.delete_proposals_for_season(dynasty_id, team_id, season)
        assert deleted_count == 5

        remaining = api.get_proposal_history(dynasty_id, team_id, season)
        assert len(remaining) == 0
