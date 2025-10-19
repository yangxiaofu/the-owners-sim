"""
Offseason Event Scheduler

Schedules all offseason events (deadlines, windows, milestones) into the event database
after the Super Bowl completes.
"""

from typing import Dict, List, Any
from datetime import datetime

from calendar.date_models import Date
from calendar.season_milestones import SeasonMilestoneCalculator, MilestoneType
from events.deadline_event import DeadlineEvent, DeadlineType
from events.window_event import WindowEvent, WindowName
from events.milestone_event import MilestoneEvent
from events.event_database_api import EventDatabaseAPI


class OffseasonEventScheduler:
    """Schedules all NFL offseason events after Super Bowl completion."""

    def __init__(self):
        self.milestone_calculator = SeasonMilestoneCalculator()

    def schedule_offseason_events(
        self,
        super_bowl_date: Date,
        season_year: int,
        dynasty_id: str,
        event_db: EventDatabaseAPI
    ) -> Dict[str, Any]:
        """
        Schedule all offseason events after Super Bowl.

        Args:
            super_bowl_date: Date when Super Bowl was played
            season_year: Current season year (e.g., 2024)
            dynasty_id: Dynasty context
            event_db: Event database API for inserting events

        Returns:
            Summary dict with counts of events scheduled
        """
        print(f"[EVENT_SCHEDULER] Step 1: Calculating milestones...")
        print(f"  Super Bowl date: {super_bowl_date}")
        print(f"  Season year: {season_year}")

        # Calculate all milestones
        milestones = self.milestone_calculator.calculate_milestones_for_season(
            season_year=season_year,
            super_bowl_date=super_bowl_date
        )
        print(f"[EVENT_SCHEDULER] ✓ Milestones calculated: {len(milestones)}")

        # Schedule different event types
        print(f"[EVENT_SCHEDULER] Step 2: Scheduling deadline events...")
        deadline_count = self._schedule_deadline_events(milestones, season_year, dynasty_id, event_db)
        print(f"[EVENT_SCHEDULER] ✓ Deadline events scheduled: {deadline_count}")

        print(f"[EVENT_SCHEDULER] Step 3: Scheduling window events...")
        window_count = self._schedule_window_events(milestones, season_year, dynasty_id, event_db)
        print(f"[EVENT_SCHEDULER] ✓ Window events scheduled: {window_count}")

        print(f"[EVENT_SCHEDULER] Step 4: Scheduling milestone events...")
        milestone_count = self._schedule_milestone_events(milestones, season_year, dynasty_id, event_db)
        print(f"[EVENT_SCHEDULER] ✓ Milestone events scheduled: {milestone_count}")

        total = deadline_count + window_count + milestone_count
        print(f"[EVENT_SCHEDULER] ✓ COMPLETE: Total events scheduled: {total}")

        return {
            "total_events": total,
            "deadline_events": deadline_count,
            "window_events": window_count,
            "milestone_events": milestone_count,
            "season_year": season_year,
            "dynasty_id": dynasty_id
        }

    def _schedule_deadline_events(
        self,
        milestones: List[Any],
        season_year: int,
        dynasty_id: str,
        event_db: EventDatabaseAPI
    ) -> int:
        """
        Schedule all deadline events.

        Args:
            milestones: List of calculated season milestones
            season_year: Current season year
            dynasty_id: Dynasty context
            event_db: Event database API

        Returns:
            Number of deadline events scheduled
        """
        count = 0

        # Try to find milestones from calculator, otherwise use fixed dates
        milestone_dict = {m.milestone_type: m for m in milestones}

        # 1. Franchise Tag Deadline (March 4)
        franchise_tag_milestone = milestone_dict.get(MilestoneType.FRANCHISE_TAG_DEADLINE)
        franchise_tag_date = franchise_tag_milestone.date if franchise_tag_milestone else Date(season_year + 1, 3, 4)
        franchise_tag_event = DeadlineEvent(
            deadline_type=DeadlineType.FRANCHISE_TAG,
            description="Franchise Tag Deadline - Teams must designate franchise-tagged players by 4 PM ET",
            season_year=season_year,
            event_date=franchise_tag_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(franchise_tag_event)
        count += 1

        # 2. Salary Cap Compliance Deadline (March 12)
        salary_cap_milestone = milestone_dict.get(MilestoneType.SALARY_CAP_DEADLINE)
        cap_compliance_date = salary_cap_milestone.date if salary_cap_milestone else Date(season_year + 1, 3, 12)
        cap_compliance_event = DeadlineEvent(
            deadline_type=DeadlineType.SALARY_CAP_COMPLIANCE,
            description="Salary Cap Compliance Deadline - Teams must be under the cap by 4 PM ET",
            season_year=season_year,
            event_date=cap_compliance_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(cap_compliance_event)
        count += 1

        # 3. RFA Tender Deadline (April 22)
        rfa_milestone = milestone_dict.get(MilestoneType.RFA_OFFER_DEADLINE)
        rfa_tender_date = rfa_milestone.date if rfa_milestone else Date(season_year + 1, 4, 22)
        rfa_tender_event = DeadlineEvent(
            deadline_type=DeadlineType.RFA_TENDER,
            description="RFA Tender Deadline - Teams must tender restricted free agents",
            season_year=season_year,
            event_date=rfa_tender_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(rfa_tender_event)
        count += 1

        # 4. Final Roster Cuts Deadline (August 26)
        roster_cuts_milestone = milestone_dict.get(MilestoneType.ROSTER_CUTS)
        roster_cuts_date = roster_cuts_milestone.date if roster_cuts_milestone else Date(season_year + 1, 8, 26)
        roster_cuts_event = DeadlineEvent(
            deadline_type=DeadlineType.FINAL_ROSTER_CUTS,
            description="Final Roster Cuts - Teams must reduce to 53-man roster by 4 PM ET",
            season_year=season_year,
            event_date=roster_cuts_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(roster_cuts_event)
        count += 1

        # 5. June 1 Releases Deadline (June 1)
        june_1_date = Date(season_year + 1, 6, 1)
        june_1_event = DeadlineEvent(
            deadline_type=DeadlineType.JUNE_1_RELEASES,
            description="June 1 Releases - Salary cap implications for post-June 1 designations take effect",
            season_year=season_year,
            event_date=june_1_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(june_1_event)
        count += 1

        return count

    def _schedule_window_events(
        self,
        milestones: List[Any],
        season_year: int,
        dynasty_id: str,
        event_db: EventDatabaseAPI
    ) -> int:
        """
        Schedule all window events (START and END pairs).

        Args:
            milestones: List of calculated season milestones
            season_year: Current season year
            dynasty_id: Dynasty context
            event_db: Event database API

        Returns:
            Number of window events scheduled (includes both START and END events)
        """
        count = 0

        # Try to find milestones from calculator
        milestone_dict = {m.milestone_type: m for m in milestones}

        # 1. Legal Tampering Window (March 10 → March 12)
        legal_tampering_milestone = milestone_dict.get(MilestoneType.LEGAL_TAMPERING_START)
        legal_tampering_start = legal_tampering_milestone.date if legal_tampering_milestone else Date(season_year + 1, 3, 10)

        legal_tampering_start_event = WindowEvent(
            window_name=WindowName.LEGAL_TAMPERING,
            window_type="START",
            description="Legal Tampering Period Begins - Teams may negotiate with other teams' free agents",
            season_year=season_year,
            event_date=legal_tampering_start,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(legal_tampering_start_event)
        count += 1

        # End of legal tampering is same as new league year
        new_league_year_milestone = milestone_dict.get(MilestoneType.NEW_LEAGUE_YEAR)
        legal_tampering_end = new_league_year_milestone.date if new_league_year_milestone else Date(season_year + 1, 3, 12)

        legal_tampering_end_event = WindowEvent(
            window_name=WindowName.LEGAL_TAMPERING,
            window_type="END",
            description="Legal Tampering Period Ends - Free agency signing period begins",
            season_year=season_year,
            event_date=legal_tampering_end,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(legal_tampering_end_event)
        count += 1

        # 2. Free Agency Signing Period (March 12 → ongoing)
        free_agency_milestone = milestone_dict.get(MilestoneType.FREE_AGENCY)
        free_agency_start = free_agency_milestone.date if free_agency_milestone else Date(season_year + 1, 3, 12)

        free_agency_start_event = WindowEvent(
            window_name=WindowName.FREE_AGENCY,
            window_type="START",
            description="Free Agency Signing Period Begins - Teams may sign unrestricted free agents at 4 PM ET",
            season_year=season_year,
            event_date=free_agency_start,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(free_agency_start_event)
        count += 1

        # 3. OTA Period (May 20 → June 10)
        ota_milestone = milestone_dict.get(MilestoneType.OTA_START)
        ota_start = ota_milestone.date if ota_milestone else Date(season_year + 1, 5, 20)

        ota_start_event = WindowEvent(
            window_name=WindowName.OTA_OFFSEASON,
            window_type="START",
            description="OTA Period Begins - Organized Team Activities start",
            season_year=season_year,
            event_date=ota_start,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(ota_start_event)
        count += 1

        ota_end = Date(season_year + 1, 6, 10)
        ota_end_event = WindowEvent(
            window_name=WindowName.OTA_OFFSEASON,
            window_type="END",
            description="OTA Period Ends - Organized Team Activities conclude",
            season_year=season_year,
            event_date=ota_end,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(ota_end_event)
        count += 1

        # 4. Minicamp (June 11 → June 15)
        minicamp_milestone = milestone_dict.get(MilestoneType.MANDATORY_MINICAMP)
        minicamp_date = minicamp_milestone.date if minicamp_milestone else Date(season_year + 1, 6, 15)

        minicamp_start = Date(season_year + 1, 6, 11)
        minicamp_start_event = WindowEvent(
            window_name=WindowName.MINICAMP,
            window_type="START",
            description="Minicamp Begins - Mandatory minicamp starts",
            season_year=season_year,
            event_date=minicamp_start,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(minicamp_start_event)
        count += 1

        minicamp_end_event = WindowEvent(
            window_name=WindowName.MINICAMP,
            window_type="END",
            description="Minicamp Ends - Mandatory minicamp concludes",
            season_year=season_year,
            event_date=minicamp_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(minicamp_end_event)
        count += 1

        # 5. Training Camp (July 25 → August 15)
        training_camp_milestone = milestone_dict.get(MilestoneType.TRAINING_CAMP)
        training_camp_start = training_camp_milestone.date if training_camp_milestone else Date(season_year + 1, 7, 25)

        training_camp_start_event = WindowEvent(
            window_name=WindowName.TRAINING_CAMP,
            window_type="START",
            description="Training Camp Opens - Teams begin training camp",
            season_year=season_year,
            event_date=training_camp_start,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(training_camp_start_event)
        count += 1

        training_camp_end = Date(season_year + 1, 8, 15)
        training_camp_end_event = WindowEvent(
            window_name=WindowName.TRAINING_CAMP,
            window_type="END",
            description="Training Camp Ends - Training camp concludes",
            season_year=season_year,
            event_date=training_camp_end,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(training_camp_end_event)
        count += 1

        # 6. Preseason Games (August 10 → August 25)
        preseason_start = Date(season_year + 1, 8, 10)
        preseason_start_event = WindowEvent(
            window_name=WindowName.PRESEASON,
            window_type="START",
            description="Preseason Begins - Preseason games start",
            season_year=season_year,
            event_date=preseason_start,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(preseason_start_event)
        count += 1

        preseason_end = Date(season_year + 1, 8, 25)
        preseason_end_event = WindowEvent(
            window_name=WindowName.PRESEASON,
            window_type="END",
            description="Preseason Ends - Preseason games conclude",
            season_year=season_year,
            event_date=preseason_end,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(preseason_end_event)
        count += 1

        return count

    def _schedule_milestone_events(
        self,
        milestones: List[Any],
        season_year: int,
        dynasty_id: str,
        event_db: EventDatabaseAPI
    ) -> int:
        """
        Schedule all milestone events.

        Args:
            milestones: List of calculated season milestones
            season_year: Current season year
            dynasty_id: Dynasty context
            event_db: Event database API

        Returns:
            Number of milestone events scheduled
        """
        count = 0

        # Create dictionary for easy lookup
        milestone_dict = {m.milestone_type: m for m in milestones}

        # Define which milestone types should create MilestoneEvents
        milestone_type_map = {
            MilestoneType.DRAFT: "DRAFT",
            MilestoneType.SCHEDULE_RELEASE: "SCHEDULE_RELEASE",
            MilestoneType.NEW_LEAGUE_YEAR: "NEW_LEAGUE_YEAR",
            MilestoneType.SCOUTING_COMBINE: "COMBINE_START",
            MilestoneType.ROOKIE_MINICAMP: "ROOKIE_MINICAMP",
        }

        # Schedule milestone events from calculator
        for milestone_type, event_type in milestone_type_map.items():
            if milestone_type in milestone_dict:
                milestone = milestone_dict[milestone_type]
                milestone_event = MilestoneEvent(
                    milestone_type=event_type,
                    description=milestone.description,
                    season_year=season_year,
                    event_date=milestone.date,
                    dynasty_id=dynasty_id,
                    metadata=milestone.calculation_metadata
                )
                event_db.insert_event(milestone_event)
                count += 1

        # Add Scouting Combine End (1 week after start)
        combine_milestone = milestone_dict.get(MilestoneType.SCOUTING_COMBINE)
        if combine_milestone:
            combine_end_date = combine_milestone.date.add_days(7)
        else:
            combine_end_date = Date(season_year + 1, 3, 3)

        combine_end_event = MilestoneEvent(
            milestone_type="COMBINE_END",
            description="NFL Scouting Combine Ends - Combine activities conclude",
            season_year=season_year,
            event_date=combine_end_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(combine_end_event)
        count += 1

        # Add Draft Order Finalized (typically late March, after free agency starts)
        draft_order_date = Date(season_year + 1, 3, 20)
        draft_order_event = MilestoneEvent(
            milestone_type="DRAFT_ORDER_FINALIZED",
            description="Draft Order Finalized - Official draft order announced after trades",
            season_year=season_year,
            event_date=draft_order_date,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(draft_order_event)
        count += 1

        # Add Preseason Start (first Thursday in August - target for "Skip to New Season")
        # Calculate dynamically using SeasonMilestoneCalculator
        preseason_start_milestone = milestone_dict.get(MilestoneType.PRESEASON_START)
        if preseason_start_milestone:
            preseason_date = preseason_start_milestone.date
        else:
            # Fallback calculation if not in milestone_dict
            preseason_date = self._calculate_first_thursday_august(season_year + 1)

        preseason_start_event = MilestoneEvent(
            milestone_type="PRESEASON_START",
            description=f"Preseason Begins - First Thursday in August ({preseason_date})",
            season_year=season_year,
            event_date=preseason_date,
            dynasty_id=dynasty_id,
            metadata={"calculation": "first_thursday_august"}
        )
        event_db.insert_event(preseason_start_event)
        count += 1

        return count

    def _calculate_first_thursday_august(self, year: int) -> Date:
        """
        Calculate first Thursday in August for given year (fallback method).

        Args:
            year: Year to calculate for

        Returns:
            Date of first Thursday in August
        """
        # Start with August 1st
        aug_1 = Date(year, 8, 1)
        py_date = aug_1.to_python_date()

        # Get weekday (0=Monday, 3=Thursday, 6=Sunday)
        weekday = py_date.weekday()

        # Calculate days until Thursday
        if weekday <= 3:  # Monday through Thursday
            days_to_thursday = 3 - weekday
        else:  # Friday through Sunday
            days_to_thursday = 7 - weekday + 3

        return aug_1.add_days(days_to_thursday)
