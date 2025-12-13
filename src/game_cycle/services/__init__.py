"""
Game Cycle Services Package.

Business logic services for the stage-based game cycle.
"""

from .resigning_service import ResigningService
from .free_agency_service import FreeAgencyService
from .initialization_service import GameCycleInitializer
from .training_camp_service import TrainingCampService
from .season_init_service import SeasonInitializationService
from .cap_helper import CapHelper
from .franchise_tag_service import FranchiseTagService
from .mock_stats_generator import MockStatsGenerator, MockGameStats
from .injury_service import InjuryService
from .injury_risk_profiles import POSITION_INJURY_RISKS, get_risk_profile
from .trade_service import TradeService
from .awards_service import AwardsService
from .flex_scheduler import FlexScheduler, PlayoffImplications, FlexRecommendation, FLEX_THRESHOLD
from .award_race_coverage import AwardRaceCoverageService, AwardCoverageType, MovementType
from .staff_generator_service import StaffGeneratorService
from .owner_service import OwnerService

# Awards package (Milestone 10)
from .awards import (
    AwardType,
    PlayerCandidate,
    AwardScore,
    EligibilityResult,
    EligibilityChecker,
    MVPCriteria,
    OPOYCriteria,
    DPOYCriteria,
    OROYCriteria,
    DROYCriteria,
    CPOYCriteria,
    AllProCriteria,
    get_criteria_for_award,
    # Tollgate 3: Voting Engine
    VotingEngine,
    VotingResult,
    VoterArchetype,
    VoterProfile,
    # Tollgate 4: Result Models
    AwardResult,
    AllProTeam,
    AllProSelection,
    ProBowlRoster,
    ProBowlSelection,
    StatisticalLeaderEntry,
    StatisticalLeadersResult,
)

__all__ = [
    "ResigningService",
    "FreeAgencyService",
    "GameCycleInitializer",
    "TrainingCampService",
    "SeasonInitializationService",
    "CapHelper",
    "FranchiseTagService",
    "MockStatsGenerator",
    "MockGameStats",
    "InjuryService",
    "POSITION_INJURY_RISKS",
    "get_risk_profile",
    "TradeService",
    "AwardsService",
    # Flex Scheduling (Milestone 11)
    "FlexScheduler",
    "PlayoffImplications",
    "FlexRecommendation",
    "FLEX_THRESHOLD",
    # Award Race Coverage (Milestone 12, Tollgate 5)
    "AwardRaceCoverageService",
    "AwardCoverageType",
    "MovementType",
    # Awards (Milestone 10)
    "AwardType",
    "PlayerCandidate",
    "AwardScore",
    "EligibilityResult",
    "EligibilityChecker",
    "MVPCriteria",
    "OPOYCriteria",
    "DPOYCriteria",
    "OROYCriteria",
    "DROYCriteria",
    "CPOYCriteria",
    "AllProCriteria",
    "get_criteria_for_award",
    # Tollgate 3: Voting Engine
    "VotingEngine",
    "VotingResult",
    "VoterArchetype",
    "VoterProfile",
    # Tollgate 4: Result Models
    "AwardResult",
    "AllProTeam",
    "AllProSelection",
    "ProBowlRoster",
    "ProBowlSelection",
    "StatisticalLeaderEntry",
    "StatisticalLeadersResult",
    # Owner Review (Milestone 13)
    "StaffGeneratorService",
    "OwnerService",
]