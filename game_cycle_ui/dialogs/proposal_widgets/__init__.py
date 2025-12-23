"""
Proposal Widgets - Type-specific display widgets for GM proposals.

Part of Tollgate 4: Approval UI.

Provides a factory function to create the appropriate widget for each proposal type.
"""

from typing import TYPE_CHECKING

from .base_widget import BaseProposalWidget
from .signing_widget import SigningProposalWidget
from .extension_widget import ExtensionProposalWidget
from .franchise_tag_widget import FranchiseTagProposalWidget
from .trade_widget import TradeProposalWidget
from .draft_pick_widget import DraftPickProposalWidget
from .cut_widget import CutProposalWidget
from .waiver_claim_widget import WaiverClaimProposalWidget

if TYPE_CHECKING:
    from game_cycle.models.persistent_gm_proposal import PersistentGMProposal

# Import ProposalType for factory mapping
from game_cycle.models.proposal_enums import ProposalType


# Widget mapping by proposal type
_WIDGET_MAP = {
    ProposalType.SIGNING: SigningProposalWidget,
    ProposalType.EXTENSION: ExtensionProposalWidget,
    ProposalType.FRANCHISE_TAG: FranchiseTagProposalWidget,
    ProposalType.TRADE: TradeProposalWidget,
    ProposalType.DRAFT_PICK: DraftPickProposalWidget,
    ProposalType.CUT: CutProposalWidget,
    ProposalType.WAIVER_CLAIM: WaiverClaimProposalWidget,
}


def create_proposal_widget(
    proposal: "PersistentGMProposal",
    parent=None,
) -> BaseProposalWidget:
    """
    Factory function to create the appropriate widget for a proposal type.

    Args:
        proposal: PersistentGMProposal to display
        parent: Parent widget

    Returns:
        Type-specific BaseProposalWidget subclass instance

    Raises:
        ValueError: If proposal type is unknown
    """
    widget_class = _WIDGET_MAP.get(proposal.proposal_type)
    if widget_class is None:
        raise ValueError(f"Unknown proposal type: {proposal.proposal_type}")

    return widget_class(proposal, parent)


__all__ = [
    "BaseProposalWidget",
    "SigningProposalWidget",
    "ExtensionProposalWidget",
    "FranchiseTagProposalWidget",
    "TradeProposalWidget",
    "DraftPickProposalWidget",
    "CutProposalWidget",
    "WaiverClaimProposalWidget",
    "create_proposal_widget",
]