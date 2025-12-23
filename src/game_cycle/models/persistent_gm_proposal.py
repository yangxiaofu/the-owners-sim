"""
Persistent GM Proposal - Database-backed proposal for owner approval.

Part of Tollgate 3: GM Proposal System persistence layer.

Design:
- General-purpose proposal model that supports all proposal types
- Persisted to database for tracking, auditing, and replay
- Type-specific details stored in JSON 'details' field
- Integrates with owner approval workflow

Note: The existing GMProposal in gm_proposal.py is FA-specific and ephemeral.
This class is the generalized, persistent version for the full Owner-GM flow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import uuid

from .proposal_enums import ProposalType, ProposalStatus


@dataclass
class PersistentGMProposal:
    """
    Database-backed GM proposal for owner approval.

    Used across all offseason stages: franchise tag, re-signing, FA, trades,
    draft, roster cuts, and waiver wire.
    """

    # Required fields
    dynasty_id: str
    """Dynasty this proposal belongs to."""

    team_id: int
    """Team making/receiving the proposal."""

    season: int
    """Season year this proposal was created."""

    stage: str
    """Stage when proposal was created (e.g., 'OFFSEASON_FREE_AGENCY')."""

    proposal_type: ProposalType
    """Type of proposal (SIGNING, TRADE, DRAFT_PICK, etc.)."""

    details: Dict[str, Any]
    """Type-specific proposal details as JSON-serializable dict."""

    gm_reasoning: str
    """GM's explanation for why this proposal makes sense."""

    # Auto-generated fields
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for this proposal."""

    # Optional context
    subject_player_id: Optional[str] = None
    """Primary player involved (if applicable)."""

    confidence: float = 0.5
    """GM's confidence in this proposal (0.0 to 1.0)."""

    # Approval workflow
    status: ProposalStatus = ProposalStatus.PENDING
    """Current status in approval workflow."""

    owner_notes: Optional[str] = None
    """Owner's notes when approving/rejecting."""

    priority: int = 0
    """Priority for ordering proposals (higher = more important)."""

    # Timestamps
    created_at: Optional[datetime] = None
    """When proposal was created."""

    resolved_at: Optional[datetime] = None
    """When proposal was approved/rejected/expired."""

    # Database ID (None until persisted)
    id: Optional[int] = None
    """Database primary key."""

    def __post_init__(self):
        """Validate proposal values."""
        self._validate_required_fields()
        self._validate_confidence()
        self._validate_details()

    def _validate_required_fields(self):
        """Ensure required fields are present and valid."""
        if not self.dynasty_id:
            raise ValueError("dynasty_id is required")

        if not isinstance(self.team_id, int) or not (1 <= self.team_id <= 32):
            raise ValueError(f"team_id must be 1-32, got {self.team_id}")

        if not self.stage:
            raise ValueError("stage is required")

        if not isinstance(self.proposal_type, ProposalType):
            raise ValueError(f"proposal_type must be ProposalType enum, got {type(self.proposal_type)}")

        if not self.gm_reasoning:
            raise ValueError("gm_reasoning is required")

    def _validate_confidence(self):
        """Ensure confidence is in valid range."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    def _validate_details(self):
        """Ensure details is a valid dict."""
        if not isinstance(self.details, dict):
            raise ValueError(f"details must be a dict, got {type(self.details)}")

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses / logging."""
        return {
            "id": self.id,
            "proposal_id": self.proposal_id,
            "dynasty_id": self.dynasty_id,
            "team_id": self.team_id,
            "season": self.season,
            "stage": self.stage,
            "proposal_type": self.proposal_type.value,
            "subject_player_id": self.subject_player_id,
            "details": self.details.copy(),
            "gm_reasoning": self.gm_reasoning,
            "confidence": self.confidence,
            "status": self.status.value,
            "owner_notes": self.owner_notes,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersistentGMProposal":
        """Create from dictionary (e.g., from API request)."""
        # Convert string enums back to enum types
        proposal_type = data.get("proposal_type")
        if isinstance(proposal_type, str):
            proposal_type = ProposalType(proposal_type)

        status = data.get("status", "PENDING")
        if isinstance(status, str):
            status = ProposalStatus(status)

        # Parse datetime strings
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        resolved_at = data.get("resolved_at")
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at)

        return cls(
            id=data.get("id"),
            proposal_id=data.get("proposal_id", str(uuid.uuid4())),
            dynasty_id=data["dynasty_id"],
            team_id=data["team_id"],
            season=data["season"],
            stage=data["stage"],
            proposal_type=proposal_type,
            subject_player_id=data.get("subject_player_id"),
            details=data.get("details", {}),
            gm_reasoning=data["gm_reasoning"],
            confidence=data.get("confidence", 0.5),
            status=status,
            owner_notes=data.get("owner_notes"),
            priority=data.get("priority", 0),
            created_at=created_at,
            resolved_at=resolved_at,
        )

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "proposal_id": self.proposal_id,
            "dynasty_id": self.dynasty_id,
            "team_id": self.team_id,
            "season": self.season,
            "stage": self.stage,
            "proposal_type": self.proposal_type.value,
            "subject_player_id": self.subject_player_id,
            "details": json.dumps(self.details),
            "gm_reasoning": self.gm_reasoning,
            "confidence": self.confidence,
            "status": self.status.value,
            "owner_notes": self.owner_notes,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "PersistentGMProposal":
        """Create from database row (sqlite3.Row or dict)."""
        # Handle sqlite3.Row by converting to dict
        if hasattr(row, "keys"):
            row = dict(row)

        # Parse JSON details
        details = row.get("details", "{}")
        if isinstance(details, str):
            details = json.loads(details)

        # Parse enums
        proposal_type = ProposalType(row["proposal_type"])
        status = ProposalStatus(row.get("status", "PENDING"))

        # Parse timestamps
        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        resolved_at = row.get("resolved_at")
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at)

        return cls(
            id=row.get("id"),
            proposal_id=row["proposal_id"],
            dynasty_id=row["dynasty_id"],
            team_id=row["team_id"],
            season=row["season"],
            stage=row["stage"],
            proposal_type=proposal_type,
            subject_player_id=row.get("subject_player_id"),
            details=details,
            gm_reasoning=row["gm_reasoning"],
            confidence=row.get("confidence", 0.5),
            status=status,
            owner_notes=row.get("owner_notes"),
            priority=row.get("priority", 0),
            created_at=created_at,
            resolved_at=resolved_at,
        )

    # =========================================================================
    # Status Transitions
    # =========================================================================

    def approve(self, notes: Optional[str] = None) -> None:
        """Mark proposal as approved."""
        self.status = ProposalStatus.APPROVED
        self.owner_notes = notes
        self.resolved_at = datetime.now()

    def reject(self, notes: Optional[str] = None) -> None:
        """Mark proposal as rejected."""
        self.status = ProposalStatus.REJECTED
        self.owner_notes = notes
        self.resolved_at = datetime.now()

    def expire(self) -> None:
        """Mark proposal as expired (e.g., stage transition)."""
        self.status = ProposalStatus.EXPIRED
        self.resolved_at = datetime.now()

    def modify(self, new_details: Dict[str, Any], notes: Optional[str] = None) -> None:
        """Mark proposal as modified with new terms."""
        self.status = ProposalStatus.MODIFIED
        self.details = new_details
        self.owner_notes = notes
        self.resolved_at = datetime.now()

    # =========================================================================
    # Status Queries
    # =========================================================================

    def is_pending(self) -> bool:
        """Check if proposal is awaiting decision."""
        return self.status == ProposalStatus.PENDING

    def is_resolved(self) -> bool:
        """Check if proposal has been decided."""
        return self.status in (
            ProposalStatus.APPROVED,
            ProposalStatus.REJECTED,
            ProposalStatus.MODIFIED,
            ProposalStatus.EXPIRED,
        )

    def is_actionable(self) -> bool:
        """Check if proposal can be executed (approved or modified)."""
        return self.status in (ProposalStatus.APPROVED, ProposalStatus.MODIFIED)

    # =========================================================================
    # Display Helpers
    # =========================================================================

    def get_type_display(self) -> str:
        """Get human-readable proposal type."""
        return self.proposal_type.value.replace("_", " ").title()

    def get_status_display(self) -> str:
        """Get human-readable status."""
        return self.status.value.title()

    def get_confidence_display(self) -> str:
        """Get confidence as percentage string."""
        return f"{int(self.confidence * 100)}%"

    def get_summary(self) -> str:
        """Get one-line summary of proposal."""
        player_info = ""
        if self.subject_player_id:
            player_name = self.details.get("player_name", self.subject_player_id)
            player_info = f" - {player_name}"

        return f"{self.get_type_display()}{player_info} ({self.get_status_display()})"


# =============================================================================
# Detail Schema Helpers
# =============================================================================

def create_franchise_tag_details(
    player_name: str,
    position: str,
    tag_type: str,  # "exclusive" or "non_exclusive"
    tag_amount: int,
    cap_impact: int,
) -> Dict[str, Any]:
    """Create details dict for FRANCHISE_TAG proposal."""
    return {
        "player_name": player_name,
        "position": position,
        "tag_type": tag_type,
        "tag_amount": tag_amount,
        "cap_impact": cap_impact,
    }


def create_extension_details(
    player_name: str,
    position: str,
    age: int,
    overall: int,
    current_contract: Dict[str, int],  # {years, total, aav}
    proposed_contract: Dict[str, int],  # {years, total, guaranteed, aav}
    market_comparison: str,
) -> Dict[str, Any]:
    """Create details dict for EXTENSION proposal."""
    return {
        "player_name": player_name,
        "position": position,
        "age": age,
        "overall": overall,
        "current_contract": current_contract,
        "proposed_contract": proposed_contract,
        "market_comparison": market_comparison,
    }


def create_signing_details(
    player_name: str,
    position: str,
    age: int,
    overall_rating: int,
    contract: Dict[str, int],  # {years, total, guaranteed, aav}
    cap_space_before: int,
    cap_space_after: int,
    competing_offers: int = 0,
) -> Dict[str, Any]:
    """Create details dict for SIGNING proposal."""
    return {
        "player_name": player_name,
        "position": position,
        "age": age,
        "overall_rating": overall_rating,
        "contract": contract,
        "cap_space_before": cap_space_before,
        "cap_space_after": cap_space_after,
        "competing_offers": competing_offers,
    }


def create_trade_details(
    trade_partner: str,
    sending: List[Dict[str, Any]],  # [{type: "player"|"pick", name, value}]
    receiving: List[Dict[str, Any]],
    value_differential: int,
    cap_impact: int,
) -> Dict[str, Any]:
    """Create details dict for TRADE proposal."""
    return {
        "trade_partner": trade_partner,
        "sending": sending,
        "receiving": receiving,
        "value_differential": value_differential,
        "cap_impact": cap_impact,
    }


def create_draft_pick_details(
    round_num: int,
    pick: int,
    overall: int,
    player_name: str,
    position: str,
    college: str,
    projected_rating: int,
    draft_grade: str,
    alternatives: List[Dict[str, Any]] = None,  # [{name, position, rating}]
) -> Dict[str, Any]:
    """Create details dict for DRAFT_PICK proposal."""
    return {
        "round": round_num,
        "pick": pick,
        "overall": overall,
        "player_name": player_name,
        "position": position,
        "college": college,
        "projected_rating": projected_rating,
        "draft_grade": draft_grade,
        "alternatives": alternatives or [],
    }


def create_cut_details(
    player_name: str,
    position: str,
    age: int,
    overall_rating: int,
    cap_savings: int,
    dead_money: int,
    replacement_options: str,
) -> Dict[str, Any]:
    """Create details dict for CUT proposal."""
    return {
        "player_name": player_name,
        "position": position,
        "age": age,
        "overall_rating": overall_rating,
        "cap_savings": cap_savings,
        "dead_money": dead_money,
        "replacement_options": replacement_options,
    }


def create_waiver_claim_details(
    player_name: str,
    position: str,
    age: int,
    overall_rating: int,
    waiver_priority: int,
    contract_remaining: Dict[str, int],  # {years, total}
) -> Dict[str, Any]:
    """Create details dict for WAIVER_CLAIM proposal."""
    return {
        "player_name": player_name,
        "position": position,
        "age": age,
        "overall_rating": overall_rating,
        "waiver_priority": waiver_priority,
        "contract_remaining": contract_remaining,
    }


def create_restructure_details(
    player_name: str,
    position: str,
    overall: int,
    age: int,
    current_cap_hit: int,
    proposed_cap_hit: int,
    cap_savings: int,
    dead_money_increase: int,
    base_salary_converted: int,
    years_remaining: int,
    contract_id: int,
    contract_year: int,
) -> Dict[str, Any]:
    """Create details dict for RESTRUCTURE proposal.

    Args:
        contract_year: The 1-based contract year being restructured (e.g., year 3 of 5).
                       This tells restructure_contract() which year's base salary to convert.
    """
    return {
        "player_name": player_name,
        "position": position,
        "overall": overall,
        "age": age,
        "current_cap_hit": current_cap_hit,
        "proposed_cap_hit": proposed_cap_hit,
        "cap_savings": cap_savings,
        "dead_money_increase": dead_money_increase,
        "base_salary_converted": base_salary_converted,
        "years_remaining": years_remaining,
        "contract_id": contract_id,
        "contract_year": contract_year,
    }