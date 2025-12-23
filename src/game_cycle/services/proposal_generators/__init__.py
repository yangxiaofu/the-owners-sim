"""
Proposal Generators - Generate GM proposals for owner approval.

Part of Tollgate 5+: Owner-GM Offseason Flow.

Each generator analyzes the game state and owner directives to produce
PersistentGMProposal objects for specific offseason stages.
"""

from .franchise_tag_generator import FranchiseTagProposalGenerator
from .resigning_generator import ResigningProposalGenerator
from .fa_signing_generator import FASigningProposalGenerator
from .trade_generator import TradeProposalGenerator
from .draft_generator import DraftProposalGenerator
from .cuts_generator import RosterCutsProposalGenerator
from .waiver_generator import WaiverProposalGenerator
from .restructure_generator import RestructureProposalGenerator
from .coach_cuts_generator import CoachCutsProposalGenerator
from .early_cuts_generator import EarlyCutsProposalGenerator
from .factory import ProposalGeneratorFactory

__all__ = [
    "FranchiseTagProposalGenerator",
    "ResigningProposalGenerator",
    "FASigningProposalGenerator",
    "TradeProposalGenerator",
    "DraftProposalGenerator",
    "RosterCutsProposalGenerator",
    "WaiverProposalGenerator",
    "RestructureProposalGenerator",
    "CoachCutsProposalGenerator",
    "EarlyCutsProposalGenerator",
    "ProposalGeneratorFactory",
]
