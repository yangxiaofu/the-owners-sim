"""
Proposal API - Database operations for GM proposals.

Part of Tollgate 3: GM Proposal System persistence layer.

Handles CRUD operations for GM proposals with dynasty isolation.
All proposals are tracked in gm_proposals table for approval workflow.
"""

import json
from datetime import datetime
from typing import List, Optional

from .connection import GameCycleDatabase
from ..models.proposal_enums import ProposalType, ProposalStatus
from ..models.persistent_gm_proposal import PersistentGMProposal


class ProposalAPI:
    """
    API for GM proposal database operations.

    Handles:
    - Creating proposals from GM generators
    - Retrieving pending proposals for owner review
    - Updating proposal status (approve/reject/expire)
    - Querying proposal history

    All operations require dynasty_id for data isolation.
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # =========================================================================
    # Create Operations
    # =========================================================================

    def create_proposal(self, proposal: PersistentGMProposal) -> str:
        """
        Create a new GM proposal.

        Args:
            proposal: PersistentGMProposal to persist

        Returns:
            proposal_id of created proposal

        Raises:
            ValueError: If proposal already exists
        """
        # Set created_at if not set
        if proposal.created_at is None:
            proposal.created_at = datetime.now()

        self.db.execute(
            """INSERT INTO gm_proposals
               (proposal_id, dynasty_id, team_id, season, stage,
                proposal_type, subject_player_id, details, gm_reasoning,
                confidence, priority, status, owner_notes, created_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                proposal.proposal_id,
                proposal.dynasty_id,
                proposal.team_id,
                proposal.season,
                proposal.stage,
                proposal.proposal_type.value,
                proposal.subject_player_id,
                json.dumps(proposal.details),
                proposal.gm_reasoning,
                proposal.confidence,
                proposal.priority,
                proposal.status.value,
                proposal.owner_notes,
                proposal.created_at.isoformat() if proposal.created_at else None,
                proposal.resolved_at.isoformat() if proposal.resolved_at else None,
            )
        )
        return proposal.proposal_id

    def create_proposals_batch(self, proposals: List[PersistentGMProposal]) -> List[str]:
        """
        Create multiple proposals in a single batch.

        Args:
            proposals: List of proposals to create

        Returns:
            List of proposal_ids created
        """
        proposal_ids = []
        for proposal in proposals:
            proposal_id = self.create_proposal(proposal)
            proposal_ids.append(proposal_id)
        return proposal_ids

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get_proposal(self, dynasty_id: str, team_id: int, proposal_id: str) -> Optional[PersistentGMProposal]:
        """
        Get a specific proposal by ID.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            proposal_id: Unique proposal ID

        Returns:
            PersistentGMProposal if found, None otherwise
        """
        row = self.db.query_one(
            """SELECT * FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND proposal_id = ?""",
            (dynasty_id, team_id, proposal_id)
        )
        if not row:
            return None
        return self._row_to_proposal(row)

    def get_pending_proposals(
        self,
        dynasty_id: str,
        team_id: int,
        stage: Optional[str] = None
    ) -> List[PersistentGMProposal]:
        """
        Get all pending proposals, optionally filtered by stage.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            stage: Optional stage filter (e.g., 'OFFSEASON_FREE_AGENCY')

        Returns:
            List of pending proposals, ordered by priority DESC then created_at
        """
        if stage:
            rows = self.db.query_all(
                """SELECT * FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND status = 'PENDING' AND stage = ?
                   ORDER BY priority DESC, created_at ASC""",
                (dynasty_id, team_id, stage)
            )
        else:
            rows = self.db.query_all(
                """SELECT * FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND status = 'PENDING'
                   ORDER BY priority DESC, created_at ASC""",
                (dynasty_id, team_id)
            )
        return [self._row_to_proposal(row) for row in rows]

    def get_proposals_by_status(
        self,
        dynasty_id: str,
        team_id: int,
        status: ProposalStatus
    ) -> List[PersistentGMProposal]:
        """
        Get proposals filtered by status.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            status: ProposalStatus to filter by

        Returns:
            List of matching proposals
        """
        rows = self.db.query_all(
            """SELECT * FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND status = ?
               ORDER BY resolved_at DESC, created_at DESC""",
            (dynasty_id, team_id, status.value)
        )
        return [self._row_to_proposal(row) for row in rows]

    def get_proposals_by_type(
        self,
        dynasty_id: str,
        team_id: int,
        proposal_type: ProposalType,
        season: Optional[int] = None
    ) -> List[PersistentGMProposal]:
        """
        Get proposals filtered by type.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            proposal_type: ProposalType to filter by
            season: Optional season filter

        Returns:
            List of matching proposals
        """
        if season:
            rows = self.db.query_all(
                """SELECT * FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND proposal_type = ? AND season = ?
                   ORDER BY created_at DESC""",
                (dynasty_id, team_id, proposal_type.value, season)
            )
        else:
            rows = self.db.query_all(
                """SELECT * FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND proposal_type = ?
                   ORDER BY created_at DESC""",
                (dynasty_id, team_id, proposal_type.value)
            )
        return [self._row_to_proposal(row) for row in rows]

    def get_proposals_by_proposer_role(
        self,
        dynasty_id: str,
        team_id: int,
        stage: str,
        proposer_role: str,
    ) -> List[PersistentGMProposal]:
        """
        Get proposals filtered by proposer role (GM or COACH).

        Filters proposals based on the proposer_role field in the details JSON.
        Used to separate GM proposals from Coach proposals in dual-recommendation workflow.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            stage: Stage name (e.g., 'OFFSEASON_ROSTER_CUTS')
            proposer_role: Proposer role filter ("GM" or "COACH")

        Returns:
            List of proposals from specified proposer, ordered by priority
        """
        rows = self.db.query_all(
            """SELECT * FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND stage = ?
                 AND json_extract(details, '$.proposer_role') = ?
               ORDER BY priority ASC, created_at ASC""",
            (dynasty_id, team_id, stage, proposer_role)
        )
        return [self._row_to_proposal(row) for row in rows]

    def get_approved_proposals(
        self,
        dynasty_id: str,
        team_id: int,
        stage: str,
        proposal_type: Optional[ProposalType] = None,
    ) -> List[PersistentGMProposal]:
        """
        Get approved proposals for a specific stage, optionally filtered by type.

        Used during stage execution to find proposals ready for processing.
        Excludes proposals already marked as executed (owner_notes contains 'EXECUTED').

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            stage: Stage name (e.g., 'OFFSEASON_TRADING')
            proposal_type: Optional ProposalType filter

        Returns:
            List of approved, non-executed proposals
        """
        if proposal_type:
            rows = self.db.query_all(
                """SELECT * FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND stage = ?
                     AND proposal_type = ? AND status = 'APPROVED'
                     AND (owner_notes IS NULL OR owner_notes NOT LIKE '%EXECUTED%')
                   ORDER BY priority ASC, created_at ASC""",
                (dynasty_id, team_id, stage, proposal_type.value)
            )
        else:
            rows = self.db.query_all(
                """SELECT * FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND stage = ?
                     AND status = 'APPROVED'
                     AND (owner_notes IS NULL OR owner_notes NOT LIKE '%EXECUTED%')
                   ORDER BY priority ASC, created_at ASC""",
                (dynasty_id, team_id, stage)
            )
        return [self._row_to_proposal(row) for row in rows]

    def mark_proposal_executed(
        self,
        dynasty_id: str,
        team_id: int,
        proposal_id: str,
    ) -> bool:
        """
        Mark an approved proposal as executed.

        Adds 'EXECUTED' tag to owner_notes to prevent re-execution.
        Status remains APPROVED for historical tracking.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            proposal_id: Proposal to mark as executed

        Returns:
            True if updated, False if not found
        """
        # Get current notes to append
        row = self.db.query_one(
            """SELECT owner_notes FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND proposal_id = ?""",
            (dynasty_id, team_id, proposal_id)
        )

        current_notes = row['owner_notes'] if row and row['owner_notes'] else ""
        if "EXECUTED" not in current_notes:
            new_notes = f"{current_notes} [EXECUTED]".strip()
        else:
            new_notes = current_notes

        cursor = self.db.execute(
            """UPDATE gm_proposals
               SET owner_notes = ?
               WHERE dynasty_id = ? AND team_id = ? AND proposal_id = ?""",
            (new_notes, dynasty_id, team_id, proposal_id)
        )
        return cursor.rowcount > 0

    def get_proposal_history(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> List[PersistentGMProposal]:
        """
        Get all proposals for a season (for history/audit).

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            List of all proposals for the season
        """
        rows = self.db.query_all(
            """SELECT * FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND season = ?
               ORDER BY created_at ASC""",
            (dynasty_id, team_id, season)
        )
        return [self._row_to_proposal(row) for row in rows]

    def count_pending_proposals(
        self,
        dynasty_id: str,
        team_id: int,
        stage: Optional[str] = None
    ) -> int:
        """
        Count pending proposals.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            stage: Optional stage filter

        Returns:
            Count of pending proposals
        """
        if stage:
            row = self.db.query_one(
                """SELECT COUNT(*) as count FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND status = 'PENDING' AND stage = ?""",
                (dynasty_id, team_id, stage)
            )
        else:
            row = self.db.query_one(
                """SELECT COUNT(*) as count FROM gm_proposals
                   WHERE dynasty_id = ? AND team_id = ? AND status = 'PENDING'""",
                (dynasty_id, team_id)
            )
        return row['count'] if row else 0

    # =========================================================================
    # Update Operations
    # =========================================================================

    def update_status(
        self,
        dynasty_id: str,
        team_id: int,
        proposal_id: str,
        status: ProposalStatus,
        owner_notes: Optional[str] = None
    ) -> bool:
        """
        Update a proposal's status.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            proposal_id: Proposal to update
            status: New status
            owner_notes: Optional owner notes

        Returns:
            True if updated, False if not found
        """
        resolved_at = datetime.now().isoformat() if status != ProposalStatus.PENDING else None

        cursor = self.db.execute(
            """UPDATE gm_proposals
               SET status = ?, owner_notes = ?, resolved_at = ?
               WHERE dynasty_id = ? AND team_id = ? AND proposal_id = ?""",
            (status.value, owner_notes, resolved_at, dynasty_id, team_id, proposal_id)
        )
        return cursor.rowcount > 0

    def approve_proposal(
        self,
        dynasty_id: str,
        team_id: int,
        proposal_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a proposal.

        Convenience method that sets status to APPROVED.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            proposal_id: Proposal to approve
            notes: Optional owner notes

        Returns:
            True if updated, False if not found
        """
        return self.update_status(
            dynasty_id, team_id, proposal_id,
            ProposalStatus.APPROVED, notes
        )

    def reject_proposal(
        self,
        dynasty_id: str,
        team_id: int,
        proposal_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Reject a proposal.

        Convenience method that sets status to REJECTED.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            proposal_id: Proposal to reject
            notes: Optional owner notes (e.g., reason for rejection)

        Returns:
            True if updated, False if not found
        """
        return self.update_status(
            dynasty_id, team_id, proposal_id,
            ProposalStatus.REJECTED, notes
        )

    def expire_pending_proposals(
        self,
        dynasty_id: str,
        team_id: int,
        stage: str
    ) -> int:
        """
        Expire all pending proposals for a stage.

        Called when transitioning to next stage to clean up unresolved proposals.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            stage: Stage whose pending proposals should be expired

        Returns:
            Number of proposals expired
        """
        resolved_at = datetime.now().isoformat()

        cursor = self.db.execute(
            """UPDATE gm_proposals
               SET status = 'EXPIRED', resolved_at = ?
               WHERE dynasty_id = ? AND team_id = ? AND stage = ? AND status = 'PENDING'""",
            (resolved_at, dynasty_id, team_id, stage)
        )
        return cursor.rowcount

    def approve_all_pending(
        self,
        dynasty_id: str,
        team_id: int,
        stage: Optional[str] = None
    ) -> int:
        """
        Approve all pending proposals (for Trust GM mode).

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            stage: Optional stage filter

        Returns:
            Number of proposals approved
        """
        resolved_at = datetime.now().isoformat()

        if stage:
            cursor = self.db.execute(
                """UPDATE gm_proposals
                   SET status = 'APPROVED', resolved_at = ?, owner_notes = 'Auto-approved (Trust GM)'
                   WHERE dynasty_id = ? AND team_id = ? AND stage = ? AND status = 'PENDING'""",
                (resolved_at, dynasty_id, team_id, stage)
            )
        else:
            cursor = self.db.execute(
                """UPDATE gm_proposals
                   SET status = 'APPROVED', resolved_at = ?, owner_notes = 'Auto-approved (Trust GM)'
                   WHERE dynasty_id = ? AND team_id = ? AND status = 'PENDING'""",
                (resolved_at, dynasty_id, team_id)
            )
        return cursor.rowcount

    # =========================================================================
    # Delete Operations
    # =========================================================================

    def delete_proposal(
        self,
        dynasty_id: str,
        team_id: int,
        proposal_id: str
    ) -> bool:
        """
        Delete a proposal.

        Generally proposals should be expired rather than deleted for audit trail.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            proposal_id: Proposal to delete

        Returns:
            True if deleted, False if not found
        """
        cursor = self.db.execute(
            """DELETE FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND proposal_id = ?""",
            (dynasty_id, team_id, proposal_id)
        )
        return cursor.rowcount > 0

    def delete_proposals_for_season(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> int:
        """
        Delete all proposals for a season.

        Use with caution - mainly for cleanup/testing.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            Number of proposals deleted
        """
        cursor = self.db.execute(
            """DELETE FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
            (dynasty_id, team_id, season)
        )
        return cursor.rowcount

    def delete_proposals_for_stage(
        self,
        dynasty_id: str,
        team_id: int,
        stage: str
    ) -> int:
        """
        Delete all proposals for a specific stage.

        Used to clear old proposals when regenerating fresh recommendations
        for a stage (e.g., preseason cuts).

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            stage: Stage name (e.g., 'OFFSEASON_PRESEASON_W1')

        Returns:
            Number of proposals deleted
        """
        cursor = self.db.execute(
            """DELETE FROM gm_proposals
               WHERE dynasty_id = ? AND team_id = ? AND stage = ?""",
            (dynasty_id, team_id, stage)
        )
        return cursor.rowcount

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_proposal(self, row) -> PersistentGMProposal:
        """Convert database row to PersistentGMProposal."""
        # Helper to safely get column value
        def get_col(name, default=None):
            try:
                return row[name] if row[name] is not None else default
            except (KeyError, IndexError):
                return default

        # Parse JSON details
        details = {}
        details_json = get_col('details')
        if details_json:
            try:
                details = json.loads(details_json)
            except (json.JSONDecodeError, TypeError):
                details = {}

        # Parse timestamps
        created_at = None
        created_at_str = get_col('created_at')
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                pass

        resolved_at = None
        resolved_at_str = get_col('resolved_at')
        if resolved_at_str:
            try:
                resolved_at = datetime.fromisoformat(resolved_at_str)
            except (ValueError, TypeError):
                pass

        return PersistentGMProposal(
            id=get_col('id'),
            proposal_id=row['proposal_id'],
            dynasty_id=row['dynasty_id'],
            team_id=row['team_id'],
            season=row['season'],
            stage=row['stage'],
            proposal_type=ProposalType(row['proposal_type']),
            subject_player_id=get_col('subject_player_id'),
            details=details,
            gm_reasoning=row['gm_reasoning'],
            confidence=get_col('confidence', 0.5),
            status=ProposalStatus(get_col('status', 'PENDING')),
            owner_notes=get_col('owner_notes'),
            priority=get_col('priority', 0),
            created_at=created_at,
            resolved_at=resolved_at,
        )