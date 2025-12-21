"""
Proposal enums for GM Proposal System.

Part of Tollgate 3: GM Proposal System persistence layer.

These enums define the types of proposals a GM can make and their resolution status.
"""

from enum import Enum


class ProposalType(Enum):
    """Types of proposals a GM can make to the owner for approval."""

    FRANCHISE_TAG = "FRANCHISE_TAG"
    """Proposal to apply franchise tag to a player."""

    EXTENSION = "EXTENSION"
    """Proposal to extend a current player's contract."""

    SIGNING = "SIGNING"
    """Proposal to sign a free agent."""

    TRADE = "TRADE"
    """Proposal to execute a trade with another team."""

    DRAFT_PICK = "DRAFT_PICK"
    """Proposal to select a player in the draft."""

    CUT = "CUT"
    """Proposal to release a player from the roster."""

    WAIVER_CLAIM = "WAIVER_CLAIM"
    """Proposal to claim a player off waivers."""

    RESTRUCTURE = "RESTRUCTURE"
    """Proposal to restructure a contract to create cap space."""


class ProposalStatus(Enum):
    """Status of a GM proposal in the approval workflow."""

    PENDING = "PENDING"
    """Proposal awaiting owner decision."""

    APPROVED = "APPROVED"
    """Owner approved the proposal - ready for execution."""

    REJECTED = "REJECTED"
    """Owner rejected the proposal."""

    MODIFIED = "MODIFIED"
    """Owner modified the proposal terms (used for counter-offers)."""

    EXPIRED = "EXPIRED"
    """Proposal expired due to stage transition or time limit."""

    @staticmethod
    def normalize(status) -> 'ProposalStatus':
        """Convert string or enum to ProposalStatus enum."""
        if isinstance(status, ProposalStatus):
            return status
        if isinstance(status, str):
            return ProposalStatus[status]
        return ProposalStatus.PENDING