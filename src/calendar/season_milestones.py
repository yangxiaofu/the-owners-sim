"""
Season Milestones

Dynamic milestone calculation system that determines key NFL calendar dates
based on actual season completion rather than fixed calendar dates.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from datetime import timedelta

from .date_models import Date
from .season_phase_tracker import SeasonPhase, GameCompletionEvent


class MilestoneType(Enum):
    """Types of NFL season milestones."""
    DRAFT = "draft"
    FREE_AGENCY = "free_agency"
    TRAINING_CAMP = "training_camp"
    SCHEDULE_RELEASE = "schedule_release"
    ROSTER_CUTS = "roster_cuts"
    TRADE_DEADLINE = "trade_deadline"
    IR_DEADLINE = "injured_reserve_deadline"
    PLAYOFF_PICTURE = "playoff_picture"
    # Offseason milestone types
    FRANCHISE_TAG_WINDOW_START = "franchise_tag_window_start"
    FRANCHISE_TAG_DEADLINE = "franchise_tag_deadline"
    TRANSITION_TAG_DEADLINE = "transition_tag_deadline"
    LEGAL_TAMPERING_START = "legal_tampering_start"
    NEW_LEAGUE_YEAR = "new_league_year"
    SALARY_CAP_DEADLINE = "salary_cap_deadline"
    RFA_OFFER_DEADLINE = "rfa_offer_deadline"
    FIFTH_YEAR_OPTION_DEADLINE = "fifth_year_option_deadline"
    SCOUTING_COMBINE = "scouting_combine"
    ROOKIE_MINICAMP = "rookie_minicamp"
    OTA_START = "ota_start"
    MANDATORY_MINICAMP = "mandatory_minicamp"
    FRANCHISE_TAG_EXTENSION_DEADLINE = "franchise_tag_extension_deadline"
    WAIVER_CLAIM_DEADLINE = "waiver_claim_deadline"


@dataclass(frozen=True)
class MilestoneDefinition:
    """Definition of how to calculate a specific milestone."""
    milestone_type: MilestoneType
    name: str
    description: str
    base_phase: SeasonPhase
    offset_calculator: Callable[[Date, Dict[str, Any]], Date]
    conditions: Dict[str, Any]
    priority: int = 1  # Lower numbers = higher priority


@dataclass(frozen=True)
class SeasonMilestone:
    """A calculated milestone with its date and metadata."""
    milestone_type: MilestoneType
    name: str
    date: Date
    description: str
    base_event: Optional[str]  # What event this milestone is based on
    calculation_metadata: Dict[str, Any]
    season_year: int


class SeasonMilestoneCalculator:
    """
    Calculates dynamic NFL season milestones based on actual season progression
    rather than fixed calendar dates.
    """

    def __init__(self):
        """Initialize with standard NFL milestone definitions."""
        self.milestone_definitions: Dict[MilestoneType, MilestoneDefinition] = {}
        self._setup_standard_milestones()

    def _setup_standard_milestones(self) -> None:
        """Set up standard NFL milestone calculations."""

        # NFL Draft - Typically 10-12 weeks after Super Bowl
        self.milestone_definitions[MilestoneType.DRAFT] = MilestoneDefinition(
            milestone_type=MilestoneType.DRAFT,
            name="NFL Draft",
            description="Annual player selection draft",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_draft_date,
            conditions={"weeks_after_super_bowl": 11, "preferred_day": "thursday"},
            priority=1
        )

        # Free Agency - Typically 2-3 weeks after Super Bowl
        self.milestone_definitions[MilestoneType.FREE_AGENCY] = MilestoneDefinition(
            milestone_type=MilestoneType.FREE_AGENCY,
            name="Free Agency Period",
            description="Unrestricted free agent signing period begins",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_free_agency_date,
            conditions={"weeks_after_super_bowl": 2, "preferred_day": "wednesday"},
            priority=2
        )

        # Training Camp - Typically 6 months after season ends (late July/early August)
        self.milestone_definitions[MilestoneType.TRAINING_CAMP] = MilestoneDefinition(
            milestone_type=MilestoneType.TRAINING_CAMP,
            name="Training Camp",
            description="Training camps open across the league",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_training_camp_date,
            conditions={"weeks_after_super_bowl": 24, "preferred_month": 8},
            priority=3
        )

        # Schedule Release - Typically 4-5 months after Super Bowl (mid-May)
        self.milestone_definitions[MilestoneType.SCHEDULE_RELEASE] = MilestoneDefinition(
            milestone_type=MilestoneType.SCHEDULE_RELEASE,
            name="Schedule Release",
            description="Next season's schedule is released",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_schedule_release_date,
            conditions={"weeks_after_super_bowl": 18, "preferred_month": 5},
            priority=4
        )

        # Trade Deadline - Typically Tuesday of Week 9 of regular season
        self.milestone_definitions[MilestoneType.TRADE_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.TRADE_DEADLINE,
            name="Trade Deadline",
            description="Deadline for trading players",
            base_phase=SeasonPhase.REGULAR_SEASON,
            offset_calculator=self._calculate_trade_deadline_date,
            conditions={"week": 9, "preferred_day": "tuesday"},
            priority=5
        )

        # Roster Cuts - Day before regular season starts
        self.milestone_definitions[MilestoneType.ROSTER_CUTS] = MilestoneDefinition(
            milestone_type=MilestoneType.ROSTER_CUTS,
            name="Final Roster Cuts",
            description="Teams must cut to 53-man roster",
            base_phase=SeasonPhase.PRESEASON,
            offset_calculator=self._calculate_roster_cuts_date,
            conditions={"days_before_regular_season": 1},
            priority=6
        )

        # Franchise Tag Window Start - 2 weeks after Super Bowl (Feb 17)
        self.milestone_definitions[MilestoneType.FRANCHISE_TAG_WINDOW_START] = MilestoneDefinition(
            milestone_type=MilestoneType.FRANCHISE_TAG_WINDOW_START,
            name="Franchise Tag Window Opens",
            description="Teams can begin applying franchise and transition tags",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_franchise_tag_window_start,
            conditions={"weeks_after_super_bowl": 2, "fixed_date": (2, 17)},
            priority=7
        )

        # Franchise Tag Deadline - March 4
        self.milestone_definitions[MilestoneType.FRANCHISE_TAG_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.FRANCHISE_TAG_DEADLINE,
            name="Franchise Tag Deadline",
            description="Deadline for teams to apply franchise or transition tags",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_franchise_tag_deadline,
            conditions={"fixed_date": (3, 4)},
            priority=8
        )

        # Transition Tag Deadline - March 4 (same as franchise tag)
        self.milestone_definitions[MilestoneType.TRANSITION_TAG_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.TRANSITION_TAG_DEADLINE,
            name="Transition Tag Deadline",
            description="Deadline for teams to apply transition tags",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_transition_tag_deadline,
            conditions={"fixed_date": (3, 4)},
            priority=8
        )

        # Legal Tampering Period Start - March 10 Noon ET
        self.milestone_definitions[MilestoneType.LEGAL_TAMPERING_START] = MilestoneDefinition(
            milestone_type=MilestoneType.LEGAL_TAMPERING_START,
            name="Legal Tampering Period Begins",
            description="Teams can negotiate with impending free agents (no signing)",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_legal_tampering_start,
            conditions={"fixed_date": (3, 10), "time": "12:00 ET"},
            priority=9
        )

        # New League Year - March 12 4PM ET
        self.milestone_definitions[MilestoneType.NEW_LEAGUE_YEAR] = MilestoneDefinition(
            milestone_type=MilestoneType.NEW_LEAGUE_YEAR,
            name="New League Year Begins",
            description="Free agent contracts can be signed, trades can be processed",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_new_league_year,
            conditions={"fixed_date": (3, 12), "time": "16:00 ET"},
            priority=10
        )

        # Salary Cap Deadline - March 12 4PM ET (same as new league year)
        self.milestone_definitions[MilestoneType.SALARY_CAP_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.SALARY_CAP_DEADLINE,
            name="Salary Cap Compliance Deadline",
            description="Teams must be under salary cap when league year begins",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_salary_cap_deadline,
            conditions={"fixed_date": (3, 12), "time": "16:00 ET"},
            priority=10
        )

        # RFA Offer Deadline - April 22
        self.milestone_definitions[MilestoneType.RFA_OFFER_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.RFA_OFFER_DEADLINE,
            name="RFA Tender Deadline",
            description="Deadline for teams to extend qualifying offers to restricted free agents",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_rfa_offer_deadline,
            conditions={"fixed_date": (4, 22)},
            priority=11
        )

        # Fifth Year Option Deadline - May 1-2
        self.milestone_definitions[MilestoneType.FIFTH_YEAR_OPTION_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.FIFTH_YEAR_OPTION_DEADLINE,
            name="Fifth Year Option Deadline",
            description="Deadline for teams to exercise fifth-year options on first-round picks",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_fifth_year_option_deadline,
            conditions={"fixed_date": (5, 2)},
            priority=12
        )

        # Scouting Combine - Late February (Feb 24 - Mar 3)
        self.milestone_definitions[MilestoneType.SCOUTING_COMBINE] = MilestoneDefinition(
            milestone_type=MilestoneType.SCOUTING_COMBINE,
            name="NFL Scouting Combine",
            description="Annual scouting combine for draft-eligible players",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_scouting_combine,
            conditions={"fixed_date": (2, 24), "duration_days": 7},
            priority=13
        )

        # Rookie Minicamp - Early May (after draft)
        self.milestone_definitions[MilestoneType.ROOKIE_MINICAMP] = MilestoneDefinition(
            milestone_type=MilestoneType.ROOKIE_MINICAMP,
            name="Rookie Minicamp",
            description="Teams hold minicamp for drafted rookies",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_rookie_minicamp,
            conditions={"weeks_after_draft": 1, "fixed_estimate": (5, 10)},
            priority=14
        )

        # OTA Start - Late May
        self.milestone_definitions[MilestoneType.OTA_START] = MilestoneDefinition(
            milestone_type=MilestoneType.OTA_START,
            name="OTA Period Begins",
            description="Organized Team Activities (OTAs) begin",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_ota_start,
            conditions={"fixed_date": (5, 20)},
            priority=15
        )

        # Mandatory Minicamp - Mid June
        self.milestone_definitions[MilestoneType.MANDATORY_MINICAMP] = MilestoneDefinition(
            milestone_type=MilestoneType.MANDATORY_MINICAMP,
            name="Mandatory Minicamp",
            description="Teams hold mandatory minicamp for all players",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_mandatory_minicamp,
            conditions={"fixed_date": (6, 15)},
            priority=16
        )

        # Franchise Tag Extension Deadline - July 15
        self.milestone_definitions[MilestoneType.FRANCHISE_TAG_EXTENSION_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.FRANCHISE_TAG_EXTENSION_DEADLINE,
            name="Franchise Tag Extension Deadline",
            description="Deadline for franchise-tagged players to sign long-term deals",
            base_phase=SeasonPhase.OFFSEASON,
            offset_calculator=self._calculate_franchise_tag_extension_deadline,
            conditions={"fixed_date": (7, 15)},
            priority=17
        )

        # Waiver Claim Deadline - August 27 Noon ET (day after roster cuts)
        self.milestone_definitions[MilestoneType.WAIVER_CLAIM_DEADLINE] = MilestoneDefinition(
            milestone_type=MilestoneType.WAIVER_CLAIM_DEADLINE,
            name="Waiver Claim Deadline",
            description="Deadline for waiver claims after final roster cuts",
            base_phase=SeasonPhase.PRESEASON,
            offset_calculator=self._calculate_waiver_claim_deadline,
            conditions={"fixed_date": (8, 27), "time": "12:00 ET"},
            priority=18
        )

    def calculate_milestones_for_season(self, season_year: int,
                                      super_bowl_date: Optional[Date] = None,
                                      regular_season_start: Optional[Date] = None) -> List[SeasonMilestone]:
        """
        Calculate all milestones for a given season.

        Args:
            season_year: The season year (e.g., 2024 for 2024-25 season)
            super_bowl_date: Date when Super Bowl was completed (if known)
            regular_season_start: Date when regular season started (if known)

        Returns:
            List of calculated milestones for the season
        """
        milestones = []
        context = {
            "season_year": season_year,
            "super_bowl_date": str(super_bowl_date) if super_bowl_date else None,
            "regular_season_start": str(regular_season_start) if regular_season_start else None
        }

        for milestone_def in self.milestone_definitions.values():
            try:
                milestone_date = milestone_def.offset_calculator(super_bowl_date, context)

                milestone = SeasonMilestone(
                    milestone_type=milestone_def.milestone_type,
                    name=milestone_def.name,
                    date=milestone_date,
                    description=milestone_def.description,
                    base_event="super_bowl" if super_bowl_date else "estimated",
                    calculation_metadata={
                        "conditions": milestone_def.conditions,
                        "base_phase": milestone_def.base_phase.value,
                        "calculation_context": context
                    },
                    season_year=season_year
                )

                milestones.append(milestone)

            except Exception:
                # Skip milestones that can't be calculated
                continue

        # Sort by date
        milestones.sort(key=lambda m: m.date)
        return milestones

    def calculate_milestone(self, milestone_type: MilestoneType,
                          season_year: int,
                          base_date: Optional[Date] = None,
                          context: Optional[Dict[str, Any]] = None) -> Optional[SeasonMilestone]:
        """
        Calculate a specific milestone.

        Args:
            milestone_type: Type of milestone to calculate
            season_year: Season year
            base_date: Base date for calculation (e.g., Super Bowl date)
            context: Additional context for calculation

        Returns:
            Calculated milestone or None if calculation fails
        """
        if milestone_type not in self.milestone_definitions:
            return None

        milestone_def = self.milestone_definitions[milestone_type]
        calc_context = context or {}
        calc_context.update({"season_year": season_year})

        try:
            milestone_date = milestone_def.offset_calculator(base_date, calc_context)

            return SeasonMilestone(
                milestone_type=milestone_type,
                name=milestone_def.name,
                date=milestone_date,
                description=milestone_def.description,
                base_event="calculated",
                calculation_metadata={
                    "conditions": milestone_def.conditions,
                    "base_phase": milestone_def.base_phase.value,
                    "calculation_context": calc_context
                },
                season_year=season_year
            )

        except Exception:
            return None

    def get_next_milestone(self, current_date: Date,
                          season_milestones: List[SeasonMilestone]) -> Optional[SeasonMilestone]:
        """
        Get the next upcoming milestone from current date.

        Args:
            current_date: Current date
            season_milestones: List of season milestones

        Returns:
            Next milestone or None if no upcoming milestones
        """
        future_milestones = [m for m in season_milestones if m.date > current_date]
        if future_milestones:
            return min(future_milestones, key=lambda m: m.date)
        return None

    def get_recent_milestones(self, current_date: Date,
                            season_milestones: List[SeasonMilestone],
                            days_back: int = 30) -> List[SeasonMilestone]:
        """
        Get milestones that occurred recently.

        Args:
            current_date: Current date
            season_milestones: List of season milestones
            days_back: How many days back to look

        Returns:
            List of recent milestones
        """
        cutoff_date = current_date.add_days(-days_back)
        return [m for m in season_milestones
                if cutoff_date <= m.date <= current_date]

    # Milestone calculation methods

    def _calculate_draft_date(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate NFL Draft date (typically 11 weeks after Super Bowl)."""
        if base_date is None:
            # Use standard estimate if no Super Bowl date available
            season_year = context.get("season_year", 2024)
            return Date(season_year + 1, 4, 25)  # Late April estimate

        # 11 weeks after Super Bowl, prefer Thursday
        draft_date = base_date.add_days(77)  # 11 weeks = 77 days

        # Adjust to nearest Thursday
        py_date = draft_date.to_python_date()
        days_until_thursday = (3 - py_date.weekday()) % 7  # Thursday is weekday 3
        draft_date = draft_date.add_days(days_until_thursday)

        return draft_date

    def _calculate_free_agency_date(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Free Agency start date (typically 2 weeks after Super Bowl)."""
        if base_date is None:
            # Use standard estimate
            season_year = context.get("season_year", 2024)
            return Date(season_year + 1, 3, 15)  # Mid-March estimate

        # 2 weeks after Super Bowl, prefer Wednesday
        fa_date = base_date.add_days(14)

        # Adjust to nearest Wednesday
        py_date = fa_date.to_python_date()
        days_until_wednesday = (2 - py_date.weekday()) % 7  # Wednesday is weekday 2
        fa_date = fa_date.add_days(days_until_wednesday)

        return fa_date

    def _calculate_training_camp_date(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Training Camp start date (typically late July)."""
        season_year = context.get("season_year", 2024)

        if base_date is None:
            # Use standard estimate - late July
            return Date(season_year + 1, 7, 25)

        # Approximately 24 weeks after Super Bowl, but aim for late July
        target_date = Date(season_year + 1, 7, 25)
        return target_date

    def _calculate_schedule_release_date(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Schedule Release date (typically mid-May)."""
        season_year = context.get("season_year", 2024)

        if base_date is None:
            # Use standard estimate - mid-May
            return Date(season_year + 1, 5, 15)

        # Approximately 18 weeks after Super Bowl, but aim for mid-May
        target_date = Date(season_year + 1, 5, 15)
        return target_date

    def _calculate_trade_deadline_date(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Trade Deadline (Tuesday of Week 9)."""
        # This would need regular season start date and schedule information
        # For now, use standard estimate
        season_year = context.get("season_year", 2024)
        regular_season_start = context.get("regular_season_start")

        if regular_season_start:
            # Week 9 starts 8 weeks after Week 1
            week_9_start = regular_season_start.add_days(8 * 7)
            # Find Tuesday of that week
            py_date = week_9_start.to_python_date()
            days_until_tuesday = (1 - py_date.weekday()) % 7  # Tuesday is weekday 1
            return week_9_start.add_days(days_until_tuesday)

        # Standard estimate - early November
        return Date(season_year, 11, 5)

    def _calculate_roster_cuts_date(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Final Roster Cuts date (day before regular season)."""
        season_year = context.get("season_year", 2024)
        regular_season_start = context.get("regular_season_start")

        if regular_season_start:
            return regular_season_start.add_days(-1)

        # Standard estimate - early September
        return Date(season_year, 9, 7)

    def _calculate_franchise_tag_window_start(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Franchise Tag Window Start (2 weeks after Super Bowl, typically Feb 17)."""
        season_year = context.get("season_year", 2024)

        if base_date is None:
            # Use standard estimate - Feb 17 of next year
            return Date(season_year + 1, 2, 17)

        # 2 weeks after Super Bowl
        return base_date.add_days(14)

    def _calculate_franchise_tag_deadline(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Franchise Tag Deadline (March 4, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 3, 4)  # March 4 of next year

    def _calculate_transition_tag_deadline(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Transition Tag Deadline (March 4, same as franchise tag)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 3, 4)  # March 4 of next year

    def _calculate_legal_tampering_start(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Legal Tampering Period Start (March 10 Noon ET, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 3, 10)  # March 10 of next year

    def _calculate_new_league_year(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate New League Year Start (March 12 4PM ET, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 3, 12)  # March 12 of next year

    def _calculate_salary_cap_deadline(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Salary Cap Compliance Deadline (March 12 4PM ET, same as new league year)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 3, 12)  # March 12 of next year

    def _calculate_rfa_offer_deadline(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate RFA Tender Deadline (April 22, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 4, 22)  # April 22 of next year

    def _calculate_fifth_year_option_deadline(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Fifth Year Option Deadline (May 2, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 5, 2)  # May 2 of next year

    def _calculate_scouting_combine(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Scouting Combine start date (Late February, Feb 24-Mar 3)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 2, 24)  # Feb 24 of next year

    def _calculate_rookie_minicamp(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Rookie Minicamp (Early May, 1 week after draft)."""
        season_year = context.get("season_year", 2024)

        # If we have draft date in context, use it
        draft_date = context.get("draft_date")
        if draft_date:
            return draft_date.add_days(7)  # 1 week after draft

        # Standard estimate - early May
        return Date(season_year + 1, 5, 10)

    def _calculate_ota_start(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate OTA Start (Late May, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 5, 20)  # May 20 of next year

    def _calculate_mandatory_minicamp(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Mandatory Minicamp (Mid June, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 6, 15)  # June 15 of next year

    def _calculate_franchise_tag_extension_deadline(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Franchise Tag Extension Deadline (July 15, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year + 1, 7, 15)  # July 15 of next year

    def _calculate_waiver_claim_deadline(self, base_date: Optional[Date], context: Dict[str, Any]) -> Date:
        """Calculate Waiver Claim Deadline (August 27 Noon ET, fixed date)."""
        season_year = context.get("season_year", 2024)
        return Date(season_year, 8, 27)  # August 27 of current season year

    def add_custom_milestone(self, milestone_def: MilestoneDefinition) -> None:
        """Add a custom milestone definition."""
        self.milestone_definitions[milestone_def.milestone_type] = milestone_def

    def get_milestone_definitions(self) -> Dict[MilestoneType, MilestoneDefinition]:
        """Get all milestone definitions."""
        return self.milestone_definitions.copy()


# Factory function for easy creation
def create_season_milestone_calculator() -> SeasonMilestoneCalculator:
    """Create a standard season milestone calculator with NFL milestones."""
    return SeasonMilestoneCalculator()