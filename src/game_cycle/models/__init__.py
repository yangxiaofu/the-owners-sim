"""Game cycle models for injury system, draft direction, FA guidance, and related data structures."""

from .injury_models import (
    InjuryType,
    InjurySeverity,
    BodyPart,
    Injury,
    InjuryRisk,
    INJURY_TYPE_TO_BODY_PART,
    INJURY_SEVERITY_WEEKS,
    INJURY_TYPE_SEVERITY_RANGE,
)

from .draft_direction import (
    DraftStrategy,
    DraftDirection,
    DraftDirectionResult,
)

from .fa_guidance import (
    FAPhilosophy,
    FAGuidance,
)

from .gm_proposal import (
    GMProposal,
)

from .rivalry import (
    RivalryType,
    Rivalry,
    DIVISION_TEAMS,
    DIVISION_NAMES,
)

from .head_to_head import (
    HeadToHeadRecord,
)

from .game_slot import (
    GameSlot,
    PrimetimeAssignment,
    TEAM_MARKET_SIZE,
    get_market_score,
)

from .owner_directives import (
    OwnerDirectives,
)

from .staff_member import (
    StaffType,
    StaffMember,
    StaffCandidate,
    create_default_gm,
    create_default_hc,
)

from .proposal_enums import (
    ProposalType,
    ProposalStatus,
)

from .persistent_gm_proposal import (
    PersistentGMProposal,
    create_franchise_tag_details,
    create_extension_details,
    create_signing_details,
    create_trade_details,
    create_draft_pick_details,
    create_cut_details,
    create_waiver_claim_details,
)

from .transaction_event import (
    TransactionType,
    TransactionEvent,
)

__all__ = [
    'InjuryType',
    'InjurySeverity',
    'BodyPart',
    'Injury',
    'InjuryRisk',
    'INJURY_TYPE_TO_BODY_PART',
    'INJURY_SEVERITY_WEEKS',
    'INJURY_TYPE_SEVERITY_RANGE',
    'DraftStrategy',
    'DraftDirection',
    'DraftDirectionResult',
    'FAPhilosophy',
    'FAGuidance',
    'GMProposal',
    'RivalryType',
    'Rivalry',
    'DIVISION_TEAMS',
    'DIVISION_NAMES',
    'HeadToHeadRecord',
    'GameSlot',
    'PrimetimeAssignment',
    'TEAM_MARKET_SIZE',
    'get_market_score',
    'OwnerDirectives',
    'StaffType',
    'StaffMember',
    'StaffCandidate',
    'create_default_gm',
    'create_default_hc',
    'ProposalType',
    'ProposalStatus',
    'PersistentGMProposal',
    'create_franchise_tag_details',
    'create_extension_details',
    'create_signing_details',
    'create_trade_details',
    'create_draft_pick_details',
    'create_cut_details',
    'create_waiver_claim_details',
    'TransactionType',
    'TransactionEvent',
]
