"""
Offseason Event Scheduler

Schedules all offseason events (deadlines, windows, milestones) into the event database
after the Super Bowl completes.
"""

from typing import Dict, List, Any
from datetime import datetime

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
    from src.calendar.season_milestones import SeasonMilestoneCalculator, MilestoneType
except (ModuleNotFoundError, ImportError):
    from src.calendar.date_models import Date
    from src.calendar.season_milestones import SeasonMilestoneCalculator, MilestoneType

from events.deadline_event import DeadlineEvent, DeadlineType
from events.window_event import WindowEvent, WindowName
from events.milestone_event import MilestoneEvent
from events.schedule_release_event import ScheduleReleaseEvent
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

        # 6. Preseason Games Window (Dynamic: day before first game → last game date)
        # Try to query actual preseason game dates first (if games already generated)
        first_game_date, last_game_date = self._get_preseason_game_date_range(
            event_db=event_db,
            season_year=season_year,
            dynasty_id=dynasty_id
        )

        if first_game_date and last_game_date:
            # Games exist - use actual dates
            # Window START = day before first game (allows user to simulate from day before)
            preseason_window_start = first_game_date.add_days(-1)
            # Window END = last game date (simulation completes on final game day)
            preseason_window_end = last_game_date

            print(f"[PRESEASON_WINDOW] Using actual game dates from database:")
            print(f"  First game: {first_game_date}")
            print(f"  Window START (first game - 1): {preseason_window_start}")
            print(f"  Last game: {last_game_date}")
            print(f"  Window END (last game): {preseason_window_end}")
        else:
            # Games don't exist yet - calculate fallback dates
            # Get PRESEASON_START milestone for calculation baseline
            preseason_start_milestone = milestone_dict.get(MilestoneType.PRESEASON_START)
            if not preseason_start_milestone:
                raise RuntimeError(
                    f"PRESEASON_START milestone required for window calculation but not found. "
                    f"Check SeasonMilestoneCalculator for season {season_year}."
                )

            preseason_window_start, preseason_window_end = self._calculate_preseason_window_dates(
                preseason_start_milestone=preseason_start_milestone.date
            )

            print(f"[PRESEASON_WINDOW] Games not yet generated - using calculated fallback dates")

        # Create window START event
        preseason_start_event = WindowEvent(
            window_name=WindowName.PRESEASON,
            window_type="START",
            description=f"Preseason Game Simulation Begins - Games can be simulated starting {preseason_window_start}",
            season_year=season_year,
            event_date=preseason_window_start,
            dynasty_id=dynasty_id
        )
        event_db.insert_event(preseason_start_event)
        count += 1

        # Create window END event
        preseason_end_event = WindowEvent(
            window_name=WindowName.PRESEASON,
            window_type="END",
            description=f"Preseason Game Simulation Ends - Final preseason game on {preseason_window_end}",
            season_year=season_year,
            event_date=preseason_window_end,
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

        # Define which milestone types should create basic MilestoneEvents
        # NOTE: SCHEDULE_RELEASE excluded - uses custom ScheduleReleaseEvent
        milestone_type_map = {
            MilestoneType.DRAFT: "DRAFT",
            MilestoneType.NEW_LEAGUE_YEAR: "NEW_LEAGUE_YEAR",
            MilestoneType.SCOUTING_COMBINE: "COMBINE_START",
            MilestoneType.ROOKIE_MINICAMP: "ROOKIE_MINICAMP",
        }

        # Schedule basic milestone events from calculator
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

        # Special case: Schedule Release - uses custom event that generates games
        schedule_release_milestone = milestone_dict.get(MilestoneType.SCHEDULE_RELEASE)
        if schedule_release_milestone:
            # Get preseason start date for schedule generation
            preseason_start_milestone = milestone_dict.get(MilestoneType.PRESEASON_START)
            if not preseason_start_milestone:
                raise RuntimeError(
                    f"PRESEASON_START milestone required for schedule generation"
                )

            schedule_release_event = ScheduleReleaseEvent(
                season_year=season_year,  # Use season parameter (consistent with other milestones)
                event_date=schedule_release_milestone.date,
                dynasty_id=dynasty_id,
                event_db=event_db,
                preseason_start_date=preseason_start_milestone.date,
                metadata=schedule_release_milestone.calculation_metadata
            )
            event_db.insert_event(schedule_release_event)
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
        # Must be provided by SeasonMilestoneCalculator - no fallback
        preseason_start_milestone = milestone_dict.get(MilestoneType.PRESEASON_START)
        if not preseason_start_milestone:
            raise RuntimeError(
                f"PRESEASON_START milestone not calculated by SeasonMilestoneCalculator "
                f"for season {season_year}. Check milestone calculator implementation."
            )

        preseason_date = preseason_start_milestone.date

        preseason_start_event = MilestoneEvent(
            milestone_type="PRESEASON_START",
            description=f"Preseason Begins - First Thursday in August ({preseason_date})",
            season_year=season_year,  # Use season parameter (consistent with other events)
            event_date=preseason_date,
            dynasty_id=dynasty_id,
            metadata={"calculation": "first_thursday_august"}
        )
        event_db.insert_event(preseason_start_event)
        count += 1

        return count

    def _get_preseason_game_date_range(
        self,
        event_db: EventDatabaseAPI,
        season_year: int,
        dynasty_id: str
    ) -> tuple[Date | None, Date | None]:
        """
        Query first and last preseason game dates from database.

        This method queries the event database for all preseason games in the upcoming
        season and returns the date range (earliest to latest). Used to dynamically
        calculate PRESEASON window boundaries.

        Args:
            event_db: Event database API for querying games
            season_year: Current season year (games are for season_year + 1)
            dynasty_id: Dynasty context for isolation

        Returns:
            Tuple of (first_game_date, last_game_date) as Date objects,
            or (None, None) if no preseason games exist yet

        Example:
            >>> first, last = self._get_preseason_game_date_range(event_db, 2025, "test")
            >>> print(f"Preseason: {first} to {last}")
            Preseason: 2026-08-06 to 2026-08-27
        """
        from events.event_database_api import EventDatabaseAPI
        import sqlite3

        conn = sqlite3.connect(event_db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Query for MIN and MAX timestamps of preseason games for upcoming season
            # Games are generated with season_year + 1 (e.g., 2026 games during 2025 offseason)
            query = '''
                SELECT
                    MIN(timestamp) as first_game_timestamp,
                    MAX(timestamp) as last_game_timestamp
                FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'GAME'
                  AND json_extract(data, '$.parameters.season_type') = 'preseason'
                  AND json_extract(data, '$.parameters.season') = ?
            '''

            cursor.execute(query, (dynasty_id, season_year + 1))
            row = cursor.fetchone()

            if row and row['first_game_timestamp'] and row['last_game_timestamp']:
                # Convert timestamps (milliseconds) to Date objects
                first_datetime = datetime.fromtimestamp(row['first_game_timestamp'] / 1000)
                last_datetime = datetime.fromtimestamp(row['last_game_timestamp'] / 1000)

                first_date = Date(first_datetime.year, first_datetime.month, first_datetime.day)
                last_date = Date(last_datetime.year, last_datetime.month, last_datetime.day)

                print(f"[PRESEASON_WINDOW] Found {season_year + 1} preseason games in database:")
                print(f"  First game: {first_date}")
                print(f"  Last game: {last_date}")

                return (first_date, last_date)
            else:
                print(f"[PRESEASON_WINDOW] No preseason games found for {season_year + 1} season yet")
                return (None, None)

        except Exception as e:
            print(f"[PRESEASON_WINDOW] Error querying preseason game dates: {e}")
            return (None, None)

        finally:
            conn.close()

    def _calculate_preseason_window_dates(
        self,
        preseason_start_milestone: Date
    ) -> tuple[Date, Date]:
        """
        Calculate preseason window dates when games don't exist yet (fallback).

        Uses conservative estimates based on NFL preseason structure:
        - 3 weeks of preseason games (Hall of Fame game may start earlier)
        - Typically runs early-mid August

        Args:
            preseason_start_milestone: Official preseason start date (first Thursday in August)

        Returns:
            Tuple of (window_start, window_end) as Date objects

        Example:
            >>> milestone = Date(2026, 8, 8)  # First Thursday
            >>> start, end = self._calculate_preseason_window_dates(milestone)
            >>> print(f"Window: {start} to {end}")
            Window: 2026-08-05 to 2026-08-29
        """
        # Window START: 3 days before milestone to catch Hall of Fame game and any early games
        # (Hall of Fame game typically Thursday before official preseason week 1)
        window_start = preseason_start_milestone.add_days(-3)

        # Window END: 21 days after milestone (3 full weeks of preseason games)
        window_end = preseason_start_milestone.add_days(21)

        print(f"[PRESEASON_WINDOW] Calculated fallback window dates:")
        print(f"  Milestone (first Thursday): {preseason_start_milestone}")
        print(f"  Window START (milestone - 3 days): {window_start}")
        print(f"  Window END (milestone + 21 days): {window_end}")

        return (window_start, window_end)

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
