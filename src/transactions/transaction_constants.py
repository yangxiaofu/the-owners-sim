"""
Transaction Constants

Centralized constants for NFL transaction AI system to eliminate magic numbers.
All probability rates, modifiers, thresholds, and timing values are defined here.

Usage:
    from transactions.transaction_constants import (
        TransactionProbability,
        ProbabilityModifiers,
        GMPhilosophyThresholds
    )

    if current_week > TransactionProbability.TRADE_DEADLINE_WEEK:
        # Trades not allowed
"""


class TransactionProbability:
    """
    Base probability constants for AI transaction evaluation.

    These values control how frequently teams evaluate potential trades
    and how many transactions can occur per day.
    """

    BASE_EVALUATION_RATE = 0.05
    """
    Base daily probability of trade evaluation (5%).

    Combined with GM's trade_frequency trait:
    - Conservative GM (0.3): 1.5% per day → ~2 evaluations per season
    - Balanced GM (0.5): 2.5% per day → ~3 evaluations per season
    - Aggressive GM (0.8): 4.0% per day → ~5 evaluations per season
    """

    MAX_DAILY_PROPOSALS = 2
    """Maximum trade proposals a team can generate per day"""

    TRADE_COOLDOWN_DAYS = 7
    """Days a team must wait after executing a trade before next evaluation"""

    TRADE_DEADLINE_WEEK = 9  # Changed from 8 in 2024 to accommodate 17-game season
    """
    NFL trade deadline week (Week 9 Tuesday in early November).

    Trades allowed through end of Week 9, blocked starting Week 10.
    Updated in 2024 to align with 17-game season format.
    """


class ProbabilityModifiers:
    """
    Situational modifiers that adjust base trade evaluation probability.

    Applied multiplicatively to base probability based on team context.
    """

    PLAYOFF_PUSH = 1.5
    """
    +50% evaluation probability for teams in playoff hunt (weeks 10+).

    Applied when team's win percentage is between 0.40 and 0.60,
    indicating they're on playoff bubble.
    """

    LOSING_STREAK = 1.25
    """
    +25% evaluation probability per game in 3+ game losing streak.

    Example: 4-game streak = 1.25^2 = 1.5625x modifier
    """

    INJURY_EMERGENCY = 3.0
    """
    +200% evaluation probability if critical starter injured.

    Currently placeholder - will be implemented when injury system added.
    """

    POST_TRADE_COOLDOWN = 0.2
    """
    -80% evaluation probability during cooldown period.

    Applied for TRADE_COOLDOWN_DAYS after a trade to prevent
    excessive transaction activity.
    """

    DEADLINE_PROXIMITY = 2.0
    """
    +100% evaluation probability in final 3 days before trade deadline.

    Simulates real NFL behavior where trades spike before deadline.
    """


class GMPhilosophyThresholds:
    """
    GM personality trait thresholds for filtering trade proposals.

    These thresholds determine how GM traits affect asset preferences:
    - Above HIGH threshold: Strong preference
    - Between MEDIUM and HIGH: Moderate preference
    - Below LOW threshold: Strong avoidance
    """

    # Star Chasing (preference for high-rated players)
    STAR_CHASING_HIGH = 0.6
    """Above this: prefer 85+ OVR players in proposals"""

    STAR_CHASING_LOW = 0.4
    """Below this: avoid trading for 88+ OVR players (too expensive)"""

    # Veteran Preference (age-based filtering)
    VETERAN_PREF_HIGH = 0.7
    """Above this: prefer age 27+ veteran players"""

    VETERAN_PREF_LOW = 0.3
    """Below this: prefer age <29 younger players"""

    # Draft Pick Valuation
    DRAFT_PICK_VALUE_HIGH = 0.6
    """Above this: reluctant to trade away draft picks"""

    DRAFT_PICK_VALUE_LOW = 0.3
    """Below this: willing to trade picks for proven talent"""

    # Cap Management Philosophy
    CAP_MGMT_HIGH = 0.7
    """Above this: max 50% cap consumption per player"""

    CAP_MGMT_MEDIUM = 0.4
    """Between 0.4-0.7: max 70% cap consumption per player"""
    # Below 0.4: max 90% cap consumption (aggressive cap management)

    # Loyalty (tendency to keep long-tenured players)
    LOYALTY_HIGH = 0.7
    """Above this: avoid trading 5+ year veterans"""

    LOYALTY_LOW = 0.3
    """Below this: willing to trade any player regardless of tenure"""

    # Win-Now vs Rebuild
    WIN_NOW_HIGH = 0.7
    """Above this: prefer proven talent over draft picks"""

    REBUILD_LOW = 0.3
    """Below this: prefer draft picks and youth over veterans"""


class NFLCalendarDates:
    """
    Official NFL calendar dates for transaction windows and deadlines.

    Based on 2024-2025 NFL CBA rules. Some dates vary by year but
    these represent typical timing.
    """

    # Franchise Tag Window
    FRANCHISE_TAG_START_MONTH = 2
    FRANCHISE_TAG_START_DAY = 18  # February 18

    FRANCHISE_TAG_END_MONTH = 3
    FRANCHISE_TAG_END_DAY = 4  # March 4, 4 PM ET

    # Free Agency
    LEGAL_TAMPERING_START_MONTH = 3
    LEGAL_TAMPERING_START_DAY = 10  # March 10 (can negotiate, not sign)

    FREE_AGENCY_START_MONTH = 3
    FREE_AGENCY_START_DAY = 12  # March 12, 4 PM ET (new league year)

    # RFA Tender Deadline
    RFA_DEADLINE_MONTH = 4
    RFA_DEADLINE_DAY = 18  # April 18

    # Roster Cuts
    ROSTER_CUT_DEADLINE_MONTH = 8
    ROSTER_CUT_DEADLINE_DAY = 27  # Late August (typically Aug 27, 4 PM ET)

    # Trade Deadline
    TRADE_DEADLINE_MONTH = 11
    TRADE_DEADLINE_DAY = 5  # Early November (Week 9 Tuesday, typically Nov 5)


class PositionValueTiers:
    """
    Position value multipliers for trade value calculations.

    Based on NFL positional value analysis and salary cap data.
    Calibrated v1.1 (PRODUCTION).
    """

    # Tier 1: Premium positions (highest multipliers)
    QUARTERBACK = 2.0
    LEFT_TACKLE = 2.0
    RIGHT_TACKLE = 2.0
    EDGE_RUSHER = 1.7

    # Tier 2: High value positions
    WIDE_RECEIVER = 1.15
    CORNERBACK = 1.3
    CENTER = 1.5

    # Tier 3: Standard value positions
    RUNNING_BACK = 1.2
    TIGHT_END = 1.0
    LINEBACKER = 1.2
    SAFETY = 1.1
    GUARD = 1.0  # Both left and right guards

    # Tier 4: Lower value positions
    DEFENSIVE_TACKLE = 0.9
    NOSE_TACKLE = 0.8
    KICKER = 0.8
    PUNTER = 0.8
    FULLBACK = 1.0

    # Default multiplier for unknown positions
    DEFAULT = 1.0


class AgeCurveParameters:
    """
    Age curve parameters for player value depreciation by position group.

    Format: (peak_start, peak_end, decline_rate)
    - peak_start: Age when peak begins
    - peak_end: Age when peak ends
    - decline_rate: Annual value decline rate after peak (0.0-1.0)

    Calibrated v1.1 based on NFL career length and performance data.
    """

    QUARTERBACK = {'peak_start': 27, 'peak_end': 32, 'decline_rate': 0.08}
    RUNNING_BACK = {'peak_start': 23, 'peak_end': 27, 'decline_rate': 0.15}
    WIDE_RECEIVER = {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12}
    TIGHT_END = {'peak_start': 26, 'peak_end': 30, 'decline_rate': 0.10}
    OFFENSIVE_LINE = {'peak_start': 26, 'peak_end': 31, 'decline_rate': 0.08}
    DEFENSIVE_LINE = {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12}
    LINEBACKER = {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12}
    DEFENSIVE_BACK = {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.13}

    # Default for unknown position groups
    DEFAULT = {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12}


class TradeValueScaling:
    """
    Scaling factors for trade value calculations.

    These constants convert between different value units and apply
    calibration factors for balanced trade valuations.
    """

    # Base value calculation scaling (calibrated v1.1)
    BASE_VALUE_DIVISOR = 3.3
    """
    Divisor for base value calculation from overall rating.

    Formula: base_value = ((overall - 50) ** 1.8) / BASE_VALUE_DIVISOR

    Calibration targets:
    - 75 OVR = ~100 value units (average starter)
    - 85 OVR = ~300 value units (Pro Bowl)
    - 95 OVR = ~700 value units (Elite)
    """

    BASE_VALUE_EXPONENT = 1.8
    """Power exponent for overall rating in value formula (non-linear scaling)"""

    BASE_VALUE_OFFSET = 50
    """Offset for overall rating (50 OVR = 0 value)"""

    # Draft pick value scaling
    DRAFT_PICK_SCALING_FACTOR = 10.0
    """
    Scaling factor for Jimmy Johnson draft chart values.

    Converts chart points (pick #1 = 3000 points) to player value units.
    Calibration: Top pick (~3000 chart points) ≈ 300 value units (elite young QB)
    """

    # Contract value adjustment limits
    CONTRACT_MULTIPLIER_MIN = 0.5
    """Minimum contract value multiplier (bad contract = half value)"""

    CONTRACT_MULTIPLIER_MAX = 1.3
    """Maximum contract value multiplier (great contract = 30% bonus)"""

    # Team need multiplier range
    NEED_MULTIPLIER_MIN = 0.7
    """Minimum need multiplier (surplus position = 70% value)"""

    NEED_MULTIPLIER_MAX = 1.3
    """Maximum need multiplier (critical need = 130% value)"""

    NEED_MULTIPLIER_DEFAULT = 1.0
    """Default multiplier when team needs unknown"""


class FairnessRatings:
    """
    Trade fairness thresholds based on value ratio.

    Value ratio = team2_total_value / team1_total_value
    """

    VERY_FAIR_MIN = 0.95
    VERY_FAIR_MAX = 1.05
    """0.95-1.05: Very fair trade (within 5%)"""

    FAIR_MIN = 0.80
    FAIR_MAX = 1.20
    """0.80-1.20: Fair trade (within 20%)"""

    SLIGHTLY_UNFAIR_MIN = 0.70
    SLIGHTLY_UNFAIR_MAX = 1.30
    """0.70-1.30: Slightly unfair (within 30%)"""

    # Below 0.70 or above 1.30: Very unfair


# Backwards compatibility - export key constants at module level
BASE_EVALUATION_RATE = TransactionProbability.BASE_EVALUATION_RATE
MAX_TRANSACTIONS_PER_DAY = TransactionProbability.MAX_DAILY_PROPOSALS
TRADE_COOLDOWN_DAYS = TransactionProbability.TRADE_COOLDOWN_DAYS
TRADE_DEADLINE_WEEK = TransactionProbability.TRADE_DEADLINE_WEEK

MODIFIER_PLAYOFF_PUSH = ProbabilityModifiers.PLAYOFF_PUSH
MODIFIER_LOSING_STREAK = ProbabilityModifiers.LOSING_STREAK
MODIFIER_INJURY_EMERGENCY = ProbabilityModifiers.INJURY_EMERGENCY
MODIFIER_POST_TRADE_COOLDOWN = ProbabilityModifiers.POST_TRADE_COOLDOWN
MODIFIER_DEADLINE_PROXIMITY = ProbabilityModifiers.DEADLINE_PROXIMITY
