"""
Awards package for game_cycle.

Provides eligibility checking, scoring algorithms, and voting simulation
for NFL awards:
- MVP, OPOY, DPOY, OROY, DROY, CPOY
- All-Pro selections
- 50-voter simulation with archetypes

Part of Milestone 10: Awards System.
"""

from .models import (
    AwardType,
    PlayerCandidate,
    AwardScore,
    EligibilityResult,
    OFFENSIVE_POSITIONS,
    DEFENSIVE_POSITIONS,
    SPECIAL_TEAMS_POSITIONS,
)

from .eligibility import (
    EligibilityChecker,
    MINIMUM_GAMES,
    MINIMUM_SNAPS,
    FULL_SEASON_GAMES,
)

from .award_criteria import (
    BaseAwardCriteria,
    MVPCriteria,
    OPOYCriteria,
    DPOYCriteria,
    OROYCriteria,
    DROYCriteria,
    CPOYCriteria,
    AllProCriteria,
    get_criteria_for_award,
    MVP_POSITION_MULTIPLIERS,
    ALL_PRO_POSITION_SLOTS,
)

from .voter_archetypes import (
    VoterArchetype,
    VoterProfile,
    ARCHETYPE_WEIGHTS,
    TRADITIONAL_POSITION_BIAS,
    VOTER_DISTRIBUTION,
)

from .voting_engine import (
    VotingEngine,
    VotingResult,
    POINTS_BY_RANK,
    MAX_POINTS,
    DEFAULT_NUM_VOTERS,
)

from .result_models import (
    AwardResult,
    AllProSelection,
    AllProTeam,
    ProBowlSelection,
    ProBowlRoster,
    StatisticalLeaderEntry,
    StatisticalLeadersResult,
)

__all__ = [
    # Enums
    "AwardType",
    "VoterArchetype",
    # Dataclasses
    "PlayerCandidate",
    "AwardScore",
    "EligibilityResult",
    "VoterProfile",
    "VotingResult",
    # Constants
    "OFFENSIVE_POSITIONS",
    "DEFENSIVE_POSITIONS",
    "SPECIAL_TEAMS_POSITIONS",
    "MINIMUM_GAMES",
    "MINIMUM_SNAPS",
    "FULL_SEASON_GAMES",
    "MVP_POSITION_MULTIPLIERS",
    "ALL_PRO_POSITION_SLOTS",
    "ARCHETYPE_WEIGHTS",
    "TRADITIONAL_POSITION_BIAS",
    "VOTER_DISTRIBUTION",
    "POINTS_BY_RANK",
    "MAX_POINTS",
    "DEFAULT_NUM_VOTERS",
    # Eligibility
    "EligibilityChecker",
    # Criteria
    "BaseAwardCriteria",
    "MVPCriteria",
    "OPOYCriteria",
    "DPOYCriteria",
    "OROYCriteria",
    "DROYCriteria",
    "CPOYCriteria",
    "AllProCriteria",
    "get_criteria_for_award",
    # Voting Engine (Tollgate 3)
    "VotingEngine",
    # Result Models (Tollgate 4)
    "AwardResult",
    "AllProSelection",
    "AllProTeam",
    "ProBowlSelection",
    "ProBowlRoster",
    "StatisticalLeaderEntry",
    "StatisticalLeadersResult",
]
