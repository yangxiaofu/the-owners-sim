"""
Transaction Timing Validator

Centralized validation for all NFL transaction types based on official NFL rules and calendar.
Determines whether a transaction is allowed based on:
- Current date
- Current phase (preseason, regular_season, playoffs, offseason)
- Current week number
- NFL CBA and league rules

Based on 2024-2025 NFL rules:
- Trade deadline: Week 9 Tuesday (early November)
- Franchise tag window: February 18 - March 4
- Free agency start: March 12 (4 PM ET)
- RFA offer sheet deadline: April 18
- Roster cut deadline: Late August (typically Aug 27)
"""

from enum import Enum
from datetime import date
from typing import Tuple
from src.calendar.season_phase_tracker import SeasonPhase
from src.transactions.transaction_constants import NFLCalendarDates, TransactionProbability


class TransactionType(Enum):
    """Supported NFL transaction types."""
    TRADE = "trade"
    FRANCHISE_TAG = "franchise_tag"
    TRANSITION_TAG = "transition_tag"
    UFA_SIGNING = "ufa_signing"
    RFA_OFFER_SHEET = "rfa_offer_sheet"
    ROSTER_CUT = "roster_cut"


class TransactionTimingValidator:
    """
    Transaction timing validator for NFL rules compliance.

    Based on 2024-2025 NFL rules:
    - Trade deadline: Week 9 Tuesday, 4:00 PM ET (changed from Week 8 in 2024)
    - Trading opens: March 12, 4:00 PM ET (new league year)
    - Trading closed: After Week 9 Tuesday until March 12 of next year

    TRADE WINDOWS:
      ✅ ALLOWED:
         - Offseason: March 12 (4 PM ET) → Preseason start
         - Preseason: Entire preseason period
         - Regular Season: Week 1 → Week 9 Tuesday (4 PM ET)

      ❌ BLOCKED:
         - Early Offseason: January 1 → March 11
         - Late Regular Season: After Week 9 Tuesday → Week 18
         - Playoffs: Wild Card → Super Bowl

    NOTE: This validator uses date-only checks (no time-of-day validation).
    Trades are blocked for the entire day of the deadline (conservative approach).
    This is acceptable for daily simulation granularity.

    Franchise Tag Window: February 18 - March 4
    Free Agency Start: March 12, 4:00 PM ET
    RFA Offer Sheet Deadline: April 18
    Roster Cut Deadline: Late August (typically Aug 27)

    Example:
        >>> validator = TransactionTimingValidator(season_year=2025)
        >>> is_allowed, reason = validator.is_trade_allowed(
        ...     current_date=date(2025, 9, 15),
        ...     current_phase="regular_season",
        ...     current_week=2
        ... )
        >>> print(is_allowed)  # True - Week 2 is before trade deadline
    """

    # NFL Trade Deadline: Week 9 Tuesday (early November)
    # Using constants from transaction_constants.py
    TRADE_DEADLINE_WEEK = TransactionProbability.TRADE_DEADLINE_WEEK
    TRADE_DEADLINE_MONTH = NFLCalendarDates.TRADE_DEADLINE_MONTH
    TRADE_DEADLINE_DAY = NFLCalendarDates.TRADE_DEADLINE_DAY

    # Franchise Tag Window
    FRANCHISE_TAG_START_MONTH = NFLCalendarDates.FRANCHISE_TAG_START_MONTH
    FRANCHISE_TAG_START_DAY = NFLCalendarDates.FRANCHISE_TAG_START_DAY
    FRANCHISE_TAG_END_MONTH = NFLCalendarDates.FRANCHISE_TAG_END_MONTH
    FRANCHISE_TAG_END_DAY = NFLCalendarDates.FRANCHISE_TAG_END_DAY

    # Free Agency Start (New League Year)
    FREE_AGENCY_START_MONTH = NFLCalendarDates.FREE_AGENCY_START_MONTH
    FREE_AGENCY_START_DAY = NFLCalendarDates.FREE_AGENCY_START_DAY

    # RFA Offer Sheet Deadline
    RFA_DEADLINE_MONTH = NFLCalendarDates.RFA_DEADLINE_MONTH
    RFA_DEADLINE_DAY = NFLCalendarDates.RFA_DEADLINE_DAY

    # Roster Cut Deadline
    ROSTER_CUT_DEADLINE_MONTH = NFLCalendarDates.ROSTER_CUT_DEADLINE_MONTH
    ROSTER_CUT_DEADLINE_DAY = NFLCalendarDates.ROSTER_CUT_DEADLINE_DAY

    def __init__(self, season_year: int):
        """
        Initialize transaction timing validator.

        Args:
            season_year: NFL season year (e.g., 2025 for 2025-26 season)
        """
        self.season_year = season_year

    def is_trade_allowed(
        self,
        current_date: date,
        current_phase: SeasonPhase,
        current_week: int = 0
    ) -> Tuple[bool, str]:
        """
        Check if trades are allowed.

        NFL Trading Rules:
        - Allowed: March 12 (new league year) through Week 9 Tuesday (early November)
        - NOT Allowed: After Week 9 deadline through end of season/playoffs
        - Resumes: March 12 of next year

        Trades are allowed during:
        - Offseason (after March 12)
        - Training camp
        - Preseason
        - Regular season weeks 1-9

        Args:
            current_date: Current calendar date
            current_phase: Current phase (SeasonPhase enum: OFFSEASON, PRESEASON, REGULAR_SEASON, PLAYOFFS)
            current_week: Current week number (0 if not in regular season)

        Returns:
            Tuple of (is_allowed: bool, reason_if_not_allowed: str)

        Example:
            >>> validator = TransactionTimingValidator(2025)
            >>> is_allowed, reason = validator.is_trade_allowed(
            ...     date(2025, 11, 10),
            ...     "regular_season",
            ...     10
            ... )
            >>> print(is_allowed)  # False
            >>> print(reason)  # "Trade deadline has passed (Week 9 Tuesday)"
        """
        # Check phase-specific blocks first (playoffs)
        if current_phase == SeasonPhase.PLAYOFFS:
            return (False, "Trades not allowed during playoffs")

        # Check if before league year starts (March 12 of season_year)
        # Must compare full date, not just month/day, to handle cross-year seasons
        # (e.g., 2025 season runs Sep 2025 - Feb 2026, then offseason Mar 2026)
        march_12_this_season = date(self.season_year, self.FREE_AGENCY_START_MONTH, self.FREE_AGENCY_START_DAY)
        if current_date < march_12_this_season:
            return (
                False,
                f"Trading period begins March {self.FREE_AGENCY_START_DAY} (new league year)"
            )

        # Check if in regular season after trade deadline (by week)
        if current_phase == SeasonPhase.REGULAR_SEASON and current_week > self.TRADE_DEADLINE_WEEK:
            return (
                False,
                f"Trade deadline has passed (Week {self.TRADE_DEADLINE_WEEK} Tuesday)"
            )

        # Trades allowed in: offseason, preseason, regular season (before deadline)
        if current_phase in [SeasonPhase.OFFSEASON, SeasonPhase.PRESEASON, SeasonPhase.REGULAR_SEASON]:
            return (True, "")

        # Unknown phase - be conservative and allow
        return (True, "")

    def is_franchise_tag_allowed(self, current_date: date) -> Tuple[bool, str]:
        """
        Check if franchise tags can be applied.

        NFL Franchise Tag Rules:
        - Window: February 18 - March 4 (4 PM ET)
        - Teams can apply ONE tag (franchise OR transition, not both)
        - Consecutive tags have escalators (120% for 2nd, 144% for 3rd)

        Args:
            current_date: Current calendar date

        Returns:
            Tuple of (is_allowed: bool, reason_if_not_allowed: str)

        Example:
            >>> validator = TransactionTimingValidator(2025)
            >>> is_allowed, reason = validator.is_franchise_tag_allowed(date(2025, 3, 1))
            >>> print(is_allowed)  # True - within franchise tag window
        """
        month, day = current_date.month, current_date.day

        # Before window opens
        if (month < self.FRANCHISE_TAG_START_MONTH or
            (month == self.FRANCHISE_TAG_START_MONTH and day < self.FRANCHISE_TAG_START_DAY)):
            return (
                False,
                f"Franchise tag window opens February {self.FRANCHISE_TAG_START_DAY}"
            )

        # After window closes
        if (month > self.FRANCHISE_TAG_END_MONTH or
            (month == self.FRANCHISE_TAG_END_MONTH and day > self.FRANCHISE_TAG_END_DAY)):
            return (
                False,
                f"Franchise tag deadline was March {self.FRANCHISE_TAG_END_DAY} (4 PM ET)"
            )

        return (True, "")

    def is_transition_tag_allowed(self, current_date: date) -> Tuple[bool, str]:
        """
        Check if transition tags can be applied.

        Transition tags follow same timing rules as franchise tags.
        Window: February 18 - March 4 (4 PM ET)

        Args:
            current_date: Current calendar date

        Returns:
            Tuple of (is_allowed: bool, reason_if_not_allowed: str)
        """
        # Transition tags use same window as franchise tags
        return self.is_franchise_tag_allowed(current_date)

    def is_free_agency_signing_allowed(self, current_date: date) -> Tuple[bool, str]:
        """
        Check if free agency signings are allowed.

        NFL Free Agency Rules:
        - Legal tampering: March 10-12 (can negotiate, not sign)
        - Signings begin: March 12 (4 PM ET)
        - Allowed year-round after opening

        Args:
            current_date: Current calendar date

        Returns:
            Tuple of (is_allowed: bool, reason_if_not_allowed: str)

        Example:
            >>> validator = TransactionTimingValidator(2025)
            >>> is_allowed, reason = validator.is_free_agency_signing_allowed(date(2025, 3, 10))
            >>> print(is_allowed)  # False - before free agency opens
            >>> print(reason)  # "Free agency begins March 12 (4 PM ET)"
        """
        month, day = current_date.month, current_date.day

        # Before free agency opens
        if (month < self.FREE_AGENCY_START_MONTH or
            (month == self.FREE_AGENCY_START_MONTH and day < self.FREE_AGENCY_START_DAY)):
            return (
                False,
                f"Free agency begins March {self.FREE_AGENCY_START_DAY} (4 PM ET)"
            )

        # Free agency allowed year-round after opening
        return (True, "")

    def is_rfa_offer_sheet_allowed(self, current_date: date) -> Tuple[bool, str]:
        """
        Check if RFA offer sheets can be submitted.

        NFL RFA Rules:
        - Allowed: March 12 - April 18
        - Original team has 5 days to match offer sheet
        - Deadline: April 18

        Args:
            current_date: Current calendar date

        Returns:
            Tuple of (is_allowed: bool, reason_if_not_allowed: str)

        Example:
            >>> validator = TransactionTimingValidator(2025)
            >>> is_allowed, reason = validator.is_rfa_offer_sheet_allowed(date(2025, 4, 20))
            >>> print(is_allowed)  # False - after RFA deadline
        """
        month, day = current_date.month, current_date.day

        # Before free agency opens
        if (month < self.FREE_AGENCY_START_MONTH or
            (month == self.FREE_AGENCY_START_MONTH and day < self.FREE_AGENCY_START_DAY)):
            return (
                False,
                f"RFA offer sheets allowed starting March {self.FREE_AGENCY_START_DAY}"
            )

        # After RFA deadline
        if (month > self.RFA_DEADLINE_MONTH or
            (month == self.RFA_DEADLINE_MONTH and day > self.RFA_DEADLINE_DAY)):
            return (
                False,
                f"RFA offer sheet deadline was April {self.RFA_DEADLINE_DAY}"
            )

        return (True, "")

    def is_roster_cut_allowed(self, current_date: date) -> Tuple[bool, str]:
        """
        Check if roster cuts can be made.

        NFL Roster Cut Rules:
        - Final cut to 53: Late August (typically Aug 27, 4 PM ET)
        - Teams can cut players year-round, but 53-man deadline is late August

        This method checks if we're before the final roster cut deadline.
        After this date, rosters must be at 53 players.

        Args:
            current_date: Current calendar date

        Returns:
            Tuple of (is_allowed: bool, reason_if_not_allowed: str)
        """
        # Roster cuts can happen year-round, but there's a deadline for 53-man
        # This is more about whether the deadline has passed
        month, day = current_date.month, current_date.day

        # Check if deadline has passed
        if (month > self.ROSTER_CUT_DEADLINE_MONTH or
            (month == self.ROSTER_CUT_DEADLINE_MONTH and day > self.ROSTER_CUT_DEADLINE_DAY)):
            # After deadline - rosters must be at 53
            return (False, f"53-man roster deadline was August {self.ROSTER_CUT_DEADLINE_DAY}")

        return (True, "")

    def get_transaction_status_summary(
        self,
        current_date: date,
        current_phase: str,
        current_week: int = 0
    ) -> dict:
        """
        Get comprehensive status of all transaction types.

        Useful for debugging or displaying current transaction windows in UI.

        Args:
            current_date: Current calendar date
            current_phase: Current phase (string like "regular_season", "offseason", "preseason", "playoffs")
            current_week: Current week number

        Returns:
            dict mapping transaction type to (is_allowed, reason) tuples

        Example:
            >>> validator = TransactionTimingValidator(2025)
            >>> status = validator.get_transaction_status_summary(
            ...     date(2025, 9, 15),
            ...     "regular_season",
            ...     2
            ... )
            >>> print(status["trades"])  # (True, "")
            >>> print(status["franchise_tags"])  # (False, "Franchise tag deadline was March 4")
        """
        # Convert string phase to SeasonPhase enum
        phase_map = {
            "offseason": SeasonPhase.OFFSEASON,
            "preseason": SeasonPhase.PRESEASON,
            "regular_season": SeasonPhase.REGULAR_SEASON,
            "playoffs": SeasonPhase.PLAYOFFS,
        }
        phase_enum = phase_map.get(current_phase.lower(), SeasonPhase.OFFSEASON)

        return {
            "trades": self.is_trade_allowed(current_date, phase_enum, current_week),
            "franchise_tags": self.is_franchise_tag_allowed(current_date),
            "transition_tags": self.is_transition_tag_allowed(current_date),
            "free_agency": self.is_free_agency_signing_allowed(current_date),
            "rfa_offer_sheets": self.is_rfa_offer_sheet_allowed(current_date),
            "roster_cuts": self.is_roster_cut_allowed(current_date)
        }
