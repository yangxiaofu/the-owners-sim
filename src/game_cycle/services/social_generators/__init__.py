"""
Social Post Generators - Pluggable stage-specific generators.

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.

Follows the proposal_generators pattern:
- One generator per event type/stage
- Factory pattern for generator selection
- Shared base class for common logic
"""

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from .game_generator import GameSocialGenerator
from .award_generator import AwardSocialGenerator
from .transaction_generator import TransactionSocialGenerator
from .franchise_tag_generator import FranchiseTagSocialGenerator
from .resigning_generator import ResigningSocialGenerator
from .waiver_generator import WaiverSocialGenerator
from .draft_generator import DraftSocialGenerator
from .hof_generator import HOFSocialGenerator
from .injury_generator import InjurySocialGenerator
from .rumor_generator import RumorSocialGenerator
from .training_camp_generator import TrainingCampSocialGenerator
from .factory import SocialPostGeneratorFactory

__all__ = [
    "BaseSocialPostGenerator",
    "GeneratedSocialPost",
    "GameSocialGenerator",
    "AwardSocialGenerator",
    "TransactionSocialGenerator",
    "FranchiseTagSocialGenerator",
    "ResigningSocialGenerator",
    "WaiverSocialGenerator",
    "DraftSocialGenerator",
    "HOFSocialGenerator",
    "InjurySocialGenerator",
    "RumorSocialGenerator",
    "TrainingCampSocialGenerator",
    "SocialPostGeneratorFactory",
]
