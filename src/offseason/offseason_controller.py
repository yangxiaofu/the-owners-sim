"""
Offseason Controller

Main orchestrator for the NFL offseason simulation phase.
Manages franchise tags, free agency, draft, and roster finalization.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
import logging

from offseason.offseason_phases import OffseasonPhase
from offseason.draft_manager import DraftManager
from offseason.roster_manager import RosterManager
from offseason.free_agency_manager import FreeAgencyManager
from offseason.team_needs_analyzer import TeamNeedsAnalyzer
from offseason.market_value_calculator import MarketValueCalculator
from salary_cap.tag_manager import TagManager
from salary_cap.cap_calculator import CapCalculator
from salary_cap.cap_database_api import CapDatabaseAPI
from database.api import DatabaseAPI


class OffseasonController:
    """
    Orchestrates the NFL offseason simulation phase.

    Manages the complete offseason lifecycle:
    - Franchise tag period (March 1-5)
    - Free agency (March 11 onwards)
    - Draft (late April)
    - Roster finalization (August)

    Responsibilities:
    - Track current offseason phase and upcoming deadlines
    - Advance calendar through offseason dates
    - Validate and execute user/AI offseason actions
    - Trigger automatic events at deadlines
    - Provide data for UI display (terminal or desktop)
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        user_team_id: int,
        calendar: Optional[Any] = None,
        super_bowl_date: Optional[datetime] = None,
        enable_persistence: bool = True,
        verbose_logging: bool = True
    ):
        """
        Initialize offseason controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024)
            user_team_id: Team ID of user-controlled team (1-32)
            calendar: Shared calendar instance (or create new)
            super_bowl_date: Date of Super Bowl (for calculating offseason start)
            enable_persistence: Whether to save actions to database
            verbose_logging: Whether to print progress messages
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.user_team_id = user_team_id
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Calendar management
        if calendar:
            self.calendar = calendar
        else:
            # If no calendar provided, start at Super Bowl + 1 week
            try:
                from src.calendar.calendar_component import CalendarComponent
            except (ModuleNotFoundError, ImportError):
                from src.calendar.calendar_component import CalendarComponent
            start_date = super_bowl_date or datetime(season_year + 1, 2, 9)
            self.calendar = CalendarComponent(start_date, season_year)

        # Database APIs
        self.db_api = DatabaseAPI(database_path)
        self.cap_api = CapDatabaseAPI(database_path)

        # Specialized managers
        self.tag_manager = TagManager(database_path)
        self.cap_calculator = CapCalculator(database_path)
        self.draft_manager = DraftManager(
            database_path, dynasty_id, season_year, enable_persistence
        )
        self.roster_manager = RosterManager(
            database_path, dynasty_id, season_year, enable_persistence
        )
        self.fa_manager = FreeAgencyManager(
            database_path, dynasty_id, season_year, enable_persistence
        )

        # AI analysis services
        self.needs_analyzer = TeamNeedsAnalyzer(database_path, dynasty_id)
        self.market_calc = MarketValueCalculator()

        # State tracking
        self.current_phase = self._detect_current_phase()
        self.deadlines = self._initialize_deadlines()
        self.offseason_complete = False

        # Statistics
        self.actions_taken = []
        self.deadlines_passed = []

    # ========== Public API: Phase Management ==========

    def get_current_phase(self) -> OffseasonPhase:
        """Get current offseason phase."""
        return self.current_phase

    def get_current_date(self) -> datetime:
        """Get current calendar date."""
        return self.calendar.get_current_date()

    def get_upcoming_deadlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get upcoming deadlines.

        Args:
            limit: Maximum number of deadlines to return

        Returns:
            List of deadline dictionaries with date, type, days_remaining
        """
        current_date = self.get_current_date()

        # Convert to date for comparison
        if hasattr(current_date, 'to_python_date'):
            current_dt = current_date.to_python_date()
        elif isinstance(current_date, datetime):
            current_dt = current_date.date()
        else:
            current_dt = current_date

        upcoming = [
            d for d in self.deadlines
            if d['date'] >= current_dt
        ]
        upcoming.sort(key=lambda x: x['date'])

        # Add days remaining
        for deadline in upcoming:
            days_remaining = (deadline['date'] - current_dt).days
            deadline['days_remaining'] = days_remaining

        return upcoming[:limit]

    def is_offseason_complete(self) -> bool:
        """Check if offseason is complete (ready for next season)."""
        return self.offseason_complete

    # ========== Public API: State Summary ==========

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive current state summary.

        Returns:
            Dictionary with all key state information
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season_year': self.season_year,
            'current_date': self.get_current_date(),
            'current_phase': self.current_phase.value,
            'offseason_complete': self.offseason_complete,
            'upcoming_deadlines': self.get_upcoming_deadlines(3),
            'actions_taken': len(self.actions_taken),
        }

    # ========== Public API: Calendar Advancement ==========

    def simulate_day(self, current_date) -> Dict[str, Any]:
        """
        Simulate offseason activities for the given date (calendar managed by SeasonCycleController).

        REFACTORED: No longer advances calendar - controller handles that.
        This method only processes offseason events for the date provided.

        Args:
            current_date: Date object for the day to simulate (from controller)

        Returns:
            Dictionary with:
                - new_date: Current date (for compatibility)
                - phase_changed: Whether phase changed
                - new_phase: New phase if changed
                - deadlines_passed: List of deadline types passed
                - events_triggered: List of automatic events
        """
        # Use provided date instead of advancing calendar
        new_date = current_date

        # Check for phase change
        old_phase = self.current_phase
        self.current_phase = self._detect_current_phase()
        phase_changed = old_phase != self.current_phase

        # Check for passed deadlines
        deadlines_passed = self._check_deadlines_passed()

        # Trigger automatic events for passed deadlines
        events_triggered = []
        for deadline_type in deadlines_passed:
            self.deadlines_passed.append(deadline_type)
            event = self._trigger_deadline_event(deadline_type)
            if event:
                events_triggered.append(event)

        # Check if offseason is complete
        if self.current_phase == OffseasonPhase.COMPLETE:
            self.offseason_complete = True

        result = {
            'new_date': new_date,
            'phase_changed': phase_changed,
            'new_phase': self.current_phase.value if phase_changed else None,
            'deadlines_passed': deadlines_passed,
            'events_triggered': events_triggered,
        }

        if self.verbose_logging:
            print(f"Advanced to {new_date.strftime('%B %d, %Y')}")
            if phase_changed:
                print(f"  Phase changed: {old_phase.value} → {self.current_phase.value}")
            if deadlines_passed:
                print(f"  Deadlines passed: {', '.join(deadlines_passed)}")

        return result

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance calendar by one day and simulate (backward compatibility wrapper).

        DEPRECATED: Use simulate_day(current_date) when called from SeasonCycleController.
        This method exists for backward compatibility with demos and internal methods
        (advance_to_deadline, advance_week, etc.) that still manage their own calendar.

        Returns:
            Dictionary with:
                - new_date: Updated calendar date
                - phase_changed: Whether phase changed
                - new_phase: New phase if changed
                - deadlines_passed: List of deadline types passed
                - events_triggered: List of automatic events
        """
        # Advance calendar (for backward compatibility)
        self.calendar.advance_day()
        current_date = self.get_current_date()

        # Call simulate_day() with the current date
        return self.simulate_day(current_date)

    def advance_to_deadline(self, deadline_type: str) -> Dict[str, Any]:
        """
        Advance calendar to next occurrence of specified deadline.

        Args:
            deadline_type: Type of deadline to advance to

        Returns:
            Dictionary with advancement results and deadline details

        Raises:
            ValueError: If deadline type not found or already passed
        """
        # Find deadline
        target_deadline = None
        current_date = self.get_current_date()

        for deadline in self.deadlines:
            if deadline['type'] == deadline_type and deadline['date'] >= current_date:
                target_deadline = deadline
                break

        if not target_deadline:
            raise ValueError(
                f"Deadline '{deadline_type}' not found or already passed"
            )

        # Advance day-by-day until deadline
        days_advanced = 0
        all_events = []

        while self.get_current_date() < target_deadline['date']:
            result = self.advance_day()
            days_advanced += 1
            all_events.extend(result.get('events_triggered', []))

        if self.verbose_logging:
            print(f"Advanced {days_advanced} days to {deadline_type}")

        return {
            'deadline_type': deadline_type,
            'deadline_date': target_deadline['date'],
            'days_advanced': days_advanced,
            'current_phase': self.current_phase.value,
            'events_triggered': all_events,
        }

    def advance_to_training_camp(self) -> Dict[str, Any]:
        """
        Advance directly to training camp (ready for next season).

        Returns:
            Dictionary with advancement results
        """
        return self.advance_to_deadline('SEASON_START')

    # ========== Public API: Franchise Tag Methods ==========

    def get_franchise_tag_candidates(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get top 3 franchise tag candidates for AI team.

        Evaluates pending free agents by:
        - Tag cost vs market value
        - Position need priority
        - Cap space availability

        Returns:
            List of top 3 tag candidates with recommendations
        """
        # Step 1: Get pending free agents (Gap 1)
        pending_fas = self.cap_api.get_pending_free_agents(
            team_id=team_id,
            season=self.season_year,
            dynasty_id=self.dynasty_id,
            min_overall=75  # Only consider quality players
        )

        if not pending_fas:
            return []

        # Step 2: Analyze team needs (Gap 2)
        team_needs = self.needs_analyzer.get_top_needs(
            team_id=team_id,
            season=self.season_year,
            limit=5
        )

        # Step 3: Evaluate tag candidates (business logic)
        candidates = self._evaluate_tag_candidates(pending_fas, team_needs)

        # Step 4: Filter by cap space
        cap_space = self._get_team_cap_space(team_id)
        affordable = [c for c in candidates if c['tag_cost'] <= cap_space]

        return affordable[:3]

    def _evaluate_tag_candidates(
        self,
        pending_fas: List[Dict[str, Any]],
        team_needs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate franchise tag worthiness for each pending FA.

        Pure business logic - no database access.

        Args:
            pending_fas: List of pending free agents
            team_needs: List of team positional needs

        Returns:
            Sorted list of tag candidates with value scores
        """
        candidates = []
        need_positions = {n['position'] for n in team_needs}

        for player in pending_fas:
            # Calculate franchise tag cost (Gap 3)
            tag_cost = self.market_calc.calculate_franchise_tag_value(
                position=player['position'],
                season=self.season_year
            )

            # Calculate market value (Gap 3)
            market_value = self.market_calc.calculate_player_value(
                position=player['position'],
                overall=player['overall'],
                age=player.get('age', 27),  # Default to 27 if not available
                years_pro=player.get('years_pro', 4)  # Default to 4 if not available
            )

            # Tag value score: How much we save by tagging vs signing FA
            # Higher score = better value to tag
            tag_value_score = market_value['total_value'] - (tag_cost / 1_000_000)

            # Bonus points if position is a team need
            if player['position'] in need_positions:
                tag_value_score += 5.0

            candidates.append({
                'player_id': player['player_id'],
                'player_name': player['player_name'],
                'position': player['position'],
                'overall': player['overall'],
                'tag_cost': tag_cost,
                'market_value_aav': market_value['aav'],
                'tag_value_score': tag_value_score,
                'is_team_need': player['position'] in need_positions,
                'recommendation': 'TAG' if tag_value_score > 10 else 'CONSIDER'
            })

        # Sort by tag value score (highest first)
        return sorted(candidates, key=lambda x: x['tag_value_score'], reverse=True)

    def _get_team_cap_space(self, team_id: int) -> int:
        """
        Get team's available salary cap space.

        Returns:
            Available cap space in dollars
        """
        # TODO: Implement cap space calculation
        # For now, return a reasonable default ($20M)
        return 20_000_000

    def apply_franchise_tag(
        self,
        player_id: int,
        team_id: int,
        tag_type: str = "NON_EXCLUSIVE"
    ) -> Dict[str, Any]:
        """
        Apply franchise tag to a player.

        Creates a 1-year contract at franchise tag salary.
        Handles consecutive tag escalators (120% for 2nd, 144% for 3rd).

        Args:
            player_id: Player to tag
            team_id: Team applying tag
            tag_type: "EXCLUSIVE" or "NON_EXCLUSIVE" (default)

        Returns:
            Dictionary with:
                - tag_applied: True if successful
                - tag_type: Type of tag applied
                - tag_salary: Salary amount
                - consecutive_tag_number: 1st, 2nd, or 3rd tag
                - cap_space_remaining: Team's remaining cap space
                - error: Error message if failed

        Raises:
            ValueError: If not in franchise tag period
            ValueError: If team already used their tag
            ValueError: If team has insufficient cap space
        """
        # Validate phase
        if self.current_phase not in [
            OffseasonPhase.FRANCHISE_TAG_PERIOD,
            OffseasonPhase.PRE_FREE_AGENCY  # Allow late tags
        ]:
            raise ValueError(
                f"Cannot apply franchise tag during {self.current_phase.value} phase. "
                f"Must be during franchise tag period (March 1-5)."
            )

        # Check if team already used their tag
        tag_status = self.get_team_tag_status(team_id)
        if tag_status['total'] > 0:
            raise ValueError(
                f"Team {team_id} has already used their tag this season: "
                f"{tag_status['franchise']} franchise, {tag_status['transition']} transition"
            )

        # Get player info (position needed for tag calculation)
        # TODO: Replace with actual player query
        player_info = self._get_player_info(player_id)
        if not player_info:
            raise ValueError(f"Player {player_id} not found")

        position = player_info.get('position', 'QB')  # Default for now

        # Apply tag via TagManager
        tag_salary = self.tag_manager.apply_franchise_tag(
            player_id=player_id,
            team_id=team_id,
            season=self.season_year + 1,  # Offseason is year after season
            dynasty_id=self.dynasty_id,
            position=position,
            tag_type=tag_type,
            tag_date=self.get_current_date().date()
        )

        # Track action
        action = {
            'type': 'FRANCHISE_TAG',
            'player_id': player_id,
            'team_id': team_id,
            'tag_type': tag_type,
            'tag_salary': tag_salary,
            'date': self.get_current_date(),
        }
        self.actions_taken.append(action)

        # Get updated cap space
        cap_info = self.cap_calculator.calculate_team_cap_space(
            team_id=team_id,
            season=self.season_year + 1,
            dynasty_id=self.dynasty_id
        )

        result = {
            'tag_applied': True,
            'tag_type': tag_type,
            'tag_salary': tag_salary,
            'consecutive_tag_number': 1,  # Would come from tag_manager
            'cap_space_remaining': cap_info['effective_cap_space'],
            'player_info': player_info,
        }

        if self.verbose_logging:
            print(f"Applied {tag_type} franchise tag to player {player_id}: ${tag_salary:,}")

        return result

    def apply_transition_tag(
        self,
        player_id: int,
        team_id: int
    ) -> Dict[str, Any]:
        """
        Apply transition tag to a player.

        Creates a 1-year contract at transition tag salary (top 10 average).
        Transition tags do not have consecutive escalators.

        Args:
            player_id: Player to tag
            team_id: Team applying tag

        Returns:
            Dictionary with tag details and cap impact
        """
        # Similar validation as franchise tag
        if self.current_phase not in [
            OffseasonPhase.FRANCHISE_TAG_PERIOD,
            OffseasonPhase.PRE_FREE_AGENCY
        ]:
            raise ValueError(
                f"Cannot apply transition tag during {self.current_phase.value} phase"
            )

        # Check if team already used their tag
        tag_status = self.get_team_tag_status(team_id)
        if tag_status['total'] > 0:
            raise ValueError(f"Team {team_id} has already used their tag this season")

        # Get player position
        player_info = self._get_player_info(player_id)
        position = player_info.get('position', 'QB')

        # Apply transition tag
        tag_salary = self.tag_manager.apply_transition_tag(
            player_id=player_id,
            team_id=team_id,
            season=self.season_year + 1,
            dynasty_id=self.dynasty_id,
            position=position,
            tag_date=self.get_current_date().date()
        )

        # Track action
        action = {
            'type': 'TRANSITION_TAG',
            'player_id': player_id,
            'team_id': team_id,
            'tag_salary': tag_salary,
            'date': self.get_current_date(),
        }
        self.actions_taken.append(action)

        result = {
            'tag_applied': True,
            'tag_type': 'TRANSITION',
            'tag_salary': tag_salary,
            'player_info': player_info,
        }

        if self.verbose_logging:
            print(f"Applied transition tag to player {player_id}: ${tag_salary:,}")

        return result

    def get_team_tag_status(self, team_id: int) -> Dict[str, int]:
        """
        Get team's franchise/transition tag usage for current season.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with:
                - franchise: Number of franchise tags used (0 or 1)
                - transition: Number of transition tags used (0 or 1)
                - total: Total tags used (0 or 1, teams can only use one)
                - can_apply_tag: Whether team can still apply a tag

        NFL Rules:
            - Teams can use 1 franchise tag OR 1 transition tag per year
            - Cannot use both in same year
        """
        tag_count = self.tag_manager.get_team_tag_count(
            team_id=team_id,
            season=self.season_year + 1,  # Offseason is year after season
            dynasty_id=self.dynasty_id
        )

        tag_count['can_apply_tag'] = tag_count['total'] == 0

        return tag_count

    # ========== Public API: Free Agency Methods ==========

    def get_free_agent_pool(
        self,
        fa_type: Optional[str] = None,
        position_filter: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get list of available free agents.

        Args:
            fa_type: Filter by type ('UFA', 'RFA', 'ERFA', or None for all)
            position_filter: Optional position to filter by (QB, WR, etc.)
            min_overall: Minimum overall rating threshold
            limit: Maximum number of players to return

        Returns:
            List of free agent dictionaries with:
                - player_id, name, position, age
                - fa_type: UFA, RFA, or ERFA
                - overall_rating
                - market_value: Estimated contract (years, AAV)
                - previous_team_id
                - previous_salary
        """
        # Validate phase - free agency methods available after legal tampering starts
        if self.current_phase not in [
            OffseasonPhase.FREE_AGENCY_LEGAL_TAMPERING,
            OffseasonPhase.FREE_AGENCY_OPEN,
            OffseasonPhase.DRAFT,
            OffseasonPhase.POST_DRAFT
        ]:
            if self.verbose_logging:
                print(f"Warning: Free agency not yet open (current phase: {self.current_phase.value})")

        # Delegate to FreeAgencyManager
        free_agents = self.fa_manager.get_free_agent_pool(
            fa_type=fa_type,
            position_filter=position_filter,
            min_overall=min_overall,
            limit=limit
        )

        if self.verbose_logging:
            print(f"Found {len(free_agents)} free agents matching criteria")

        return free_agents

    def get_player_market_value(self, player_id: int) -> Dict[str, Any]:
        """
        Calculate estimated market value for a free agent.

        Args:
            player_id: Player ID

        Returns:
            Dictionary with:
                - estimated_years: Likely contract length (1-5 years)
                - estimated_aav: Annual average value
                - estimated_guarantees: Likely guaranteed money
                - estimated_total_value: Total contract value
                - factors: Key factors affecting market value
        """
        return self.fa_manager.get_player_market_value(player_id)

    def sign_free_agent(
        self,
        player_id: int,
        team_id: int,
        years: int,
        annual_salary: int,
        signing_bonus: int = 0,
        guarantees: int = 0
    ) -> Dict[str, Any]:
        """
        Sign a free agent to a contract.

        Validates cap space and creates contract in database.

        Args:
            player_id: Free agent to sign
            team_id: Team signing the player
            years: Contract length (1-5 years typical)
            annual_salary: Annual salary amount
            signing_bonus: Upfront signing bonus (prorated over contract)
            guarantees: Total guaranteed money

        Returns:
            Dictionary with:
                - signed: True if successful
                - contract_id: Database ID of created contract
                - contract_details: Years, AAV, guarantees, total value
                - cap_hit_year1: First year cap hit
                - cap_space_remaining: Team's remaining cap space
                - error: Error message if failed

        Raises:
            ValueError: If not in free agency period
            ValueError: If player not available (already signed)
            ValueError: If team has insufficient cap space
            ValueError: If contract terms are invalid
        """
        # Validate phase
        if self.current_phase not in [
            OffseasonPhase.FREE_AGENCY_OPEN,
            OffseasonPhase.DRAFT,
            OffseasonPhase.POST_DRAFT,
            OffseasonPhase.ROSTER_CUTS
        ]:
            # Legal tampering allows negotiations but not signings
            if self.current_phase == OffseasonPhase.FREE_AGENCY_LEGAL_TAMPERING:
                raise ValueError(
                    "Cannot sign free agents during legal tampering period. "
                    "Signings allowed starting March 13, 4 PM ET."
                )
            else:
                raise ValueError(
                    f"Cannot sign free agents during {self.current_phase.value} phase"
                )

        # Validate contract terms
        if years < 1 or years > 7:
            raise ValueError(f"Invalid contract length: {years} years (must be 1-7)")

        if annual_salary < 0:
            raise ValueError(f"Invalid annual salary: ${annual_salary:,}")

        total_value = annual_salary * years + signing_bonus

        # Check cap space before signing
        cap_info = self.cap_calculator.calculate_team_cap_space(
            team_id=team_id,
            season=self.season_year + 1,
            dynasty_id=self.dynasty_id
        )

        # Calculate first year cap hit (annual salary + prorated bonus)
        bonus_proration = signing_bonus // years if years > 0 else 0
        first_year_cap_hit = annual_salary + bonus_proration

        if first_year_cap_hit > cap_info['effective_cap_space']:
            raise ValueError(
                f"Insufficient cap space. Need ${first_year_cap_hit:,}, "
                f"have ${cap_info['effective_cap_space']:,}"
            )

        # Sign player via FreeAgencyManager
        signing_result = self.fa_manager.sign_free_agent(
            player_id=player_id,
            team_id=team_id,
            years=years,
            annual_salary=annual_salary,
            signing_bonus=signing_bonus,
            guarantees=guarantees
        )

        # Track action
        action = {
            'type': 'FREE_AGENT_SIGNING',
            'player_id': player_id,
            'team_id': team_id,
            'years': years,
            'annual_salary': annual_salary,
            'signing_bonus': signing_bonus,
            'total_value': total_value,
            'date': self.get_current_date(),
        }
        self.actions_taken.append(action)

        # Get updated cap space
        updated_cap_info = self.cap_calculator.calculate_team_cap_space(
            team_id=team_id,
            season=self.season_year + 1,
            dynasty_id=self.dynasty_id
        )

        result = {
            'signed': True,
            'contract_id': signing_result.get('contract_id'),
            'contract_details': {
                'years': years,
                'aav': annual_salary,
                'signing_bonus': signing_bonus,
                'guarantees': guarantees,
                'total_value': total_value,
            },
            'cap_hit_year1': first_year_cap_hit,
            'cap_space_remaining': updated_cap_info['effective_cap_space'],
            'player_info': signing_result.get('player_info'),
        }

        if self.verbose_logging:
            player_name = signing_result.get('player_info', {}).get('name', f'Player {player_id}')
            print(f"Signed {player_name} to {years}-year, ${annual_salary:,}/year contract")
            print(f"  Total value: ${total_value:,}, Guarantees: ${guarantees:,}")
            print(f"  Cap space remaining: ${updated_cap_info['effective_cap_space']:,}")

        return result

    def apply_rfa_tender(
        self,
        player_id: int,
        team_id: int,
        tender_level: str
    ) -> Dict[str, Any]:
        """
        Apply RFA tender to restricted free agent.

        Args:
            player_id: RFA player
            team_id: Team applying tender
            tender_level: "FIRST_ROUND", "SECOND_ROUND", "ORIGINAL_ROUND", "RIGHT_OF_FIRST_REFUSAL"

        Returns:
            Dictionary with tender details and compensation

        NFL Rules:
            - Deadline: Late April (after draft)
            - Player can negotiate with other teams
            - Original team has right to match offers
            - Different tender levels provide different draft pick compensation
        """
        # Get player's previous salary for tender calculation
        player_info = self._get_player_info(player_id)
        previous_salary = player_info.get('previous_salary', 0)

        # Apply tender via TagManager
        tender_salary = self.tag_manager.apply_rfa_tender(
            player_id=player_id,
            team_id=team_id,
            season=self.season_year + 1,
            dynasty_id=self.dynasty_id,
            tender_level=tender_level,
            player_previous_salary=previous_salary,
            tender_date=self.get_current_date().date()
        )

        # Track action
        action = {
            'type': 'RFA_TENDER',
            'player_id': player_id,
            'team_id': team_id,
            'tender_level': tender_level,
            'tender_salary': tender_salary,
            'date': self.get_current_date(),
        }
        self.actions_taken.append(action)

        result = {
            'tender_applied': True,
            'tender_level': tender_level,
            'tender_salary': tender_salary,
            'compensation': self._get_rfa_compensation_description(tender_level),
            'player_info': player_info,
        }

        if self.verbose_logging:
            print(f"Applied {tender_level} RFA tender to player {player_id}: ${tender_salary:,}")

        return result

    def simulate_ai_free_agency(
        self,
        user_team_id: int,
        days_to_simulate: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Simulate AI team free agency activity.

        Args:
            user_team_id: User's team (will not simulate)
            days_to_simulate: Number of days of FA activity to simulate

        Returns:
            List of all FA signings made by AI teams
        """
        if self.verbose_logging:
            print(f"Simulating {days_to_simulate} days of AI free agency activity...")

        signings = self.fa_manager.simulate_free_agency(
            user_team_id=user_team_id,
            days_to_simulate=days_to_simulate
        )

        if self.verbose_logging:
            print(f"AI teams made {len(signings)} free agent signings")

        return signings

    # ========== Public API: Draft Methods ==========

    def get_draft_board(
        self,
        team_id: int,
        position_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get team's draft board with prospect rankings.

        Args:
            team_id: Team ID (1-32)
            position_filter: Optional position to filter by
            limit: Maximum number of prospects to return

        Returns:
            List of prospect dictionaries with:
                - player_id, name, position
                - college, class (JR, SR, etc.)
                - overall_rating, ceiling, floor
                - combine_metrics (40-time, bench, etc.)
                - team_grade: Team-specific grade based on needs
                - projected_round
        """
        # Validate phase - draft board available after free agency opens
        if self.current_phase not in [
            OffseasonPhase.FREE_AGENCY_OPEN,
            OffseasonPhase.DRAFT,
            OffseasonPhase.POST_DRAFT
        ]:
            if self.verbose_logging:
                print(f"Warning: Draft board available starting free agency period")

        # Get draft board from DraftManager
        board = self.draft_manager.get_draft_board(
            team_id=team_id,
            position_filter=position_filter,
            limit=limit
        )

        if self.verbose_logging:
            print(f"Retrieved draft board for team {team_id}: {len(board)} prospects")

        return board

    def make_draft_selection(
        self,
        round_num: int,
        pick_num: int,
        player_id: str,
        team_id: int
    ) -> Dict[str, Any]:
        """
        Execute a draft pick.

        Creates rookie contract and adds player to roster.

        Args:
            round_num: Draft round (1-7)
            pick_num: Pick number within round (1-32+)
            player_id: ID of prospect being drafted
            team_id: Team making the pick

        Returns:
            Dictionary with:
                - pick_made: True if successful
                - round: Draft round
                - pick: Pick number
                - overall_pick: Overall pick number (1-224+)
                - player_info: Drafted player details
                - contract_details: Rookie contract terms
                - error: Error message if failed

        Raises:
            ValueError: If not in draft period
            ValueError: If not team's turn to pick
            ValueError: If player already drafted
        """
        # Validate phase
        if self.current_phase != OffseasonPhase.DRAFT:
            raise ValueError(
                f"Cannot make draft picks during {self.current_phase.value} phase. "
                f"Draft period is late April (typically April 24-27)."
            )

        # Validate round and pick
        if round_num < 1 or round_num > 7:
            raise ValueError(f"Invalid round: {round_num} (must be 1-7)")

        if pick_num < 1:
            raise ValueError(f"Invalid pick number: {pick_num}")

        # Calculate overall pick number
        overall_pick = ((round_num - 1) * 32) + pick_num

        # Make selection via DraftManager
        selection_result = self.draft_manager.make_draft_selection(
            round_num=round_num,
            pick_num=pick_num,
            player_id=player_id,
            team_id=team_id
        )

        # Track action
        action = {
            'type': 'DRAFT_PICK',
            'team_id': team_id,
            'round': round_num,
            'pick': pick_num,
            'overall_pick': overall_pick,
            'player_id': player_id,
            'date': self.get_current_date(),
        }
        self.actions_taken.append(action)

        result = {
            'pick_made': True,
            'round': round_num,
            'pick': pick_num,
            'overall_pick': overall_pick,
            'player_info': selection_result.get('player_info'),
            'contract_details': selection_result.get('contract_details'),
        }

        if self.verbose_logging:
            player_name = selection_result.get('player_info', {}).get('name', f'Player {player_id}')
            print(f"Round {round_num}, Pick {pick_num} (#{overall_pick} overall): "
                  f"Team {team_id} selects {player_name}")

        return result

    def simulate_draft_round(
        self,
        round_num: int,
        user_team_id: int,
        user_selections: Optional[Dict[int, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Simulate an entire draft round with AI teams.

        Args:
            round_num: Round to simulate (1-7)
            user_team_id: User's team ID
            user_selections: Optional dict of {pick_number: player_id} for user picks

        Returns:
            List of all picks made in the round
        """
        if self.verbose_logging:
            print(f"Simulating draft round {round_num}...")

        # TODO: Implement AI draft simulation for round
        # This would:
        # 1. Get draft order for the round
        # 2. For each pick:
        #    - If user's pick and user_selections provided, use that
        #    - Otherwise, AI selects best available for team needs
        # 3. Return list of all picks

        picks = []

        if self.verbose_logging:
            print(f"Round {round_num} complete: {len(picks)} picks made")

        return picks

    def simulate_entire_draft(
        self,
        user_team_id: int,
        user_picks: Optional[Dict[int, str]] = None
    ) -> Dict[str, Any]:
        """
        Simulate entire 7-round NFL Draft.

        Args:
            user_team_id: User's team ID
            user_picks: Optional dict of {overall_pick: player_id} for user selections

        Returns:
            Dictionary with:
                - total_picks: Total picks made (224+)
                - picks_by_round: List of picks for each round
                - user_team_picks: List of user's draft picks
                - notable_picks: Top-rated players drafted
        """
        if self.verbose_logging:
            print("Simulating entire NFL Draft (7 rounds)...")

        # Delegate to DraftManager
        draft_results = self.draft_manager.simulate_draft(
            user_team_id=user_team_id,
            user_picks=user_picks
        )

        # Track action
        action = {
            'type': 'DRAFT_SIMULATION',
            'total_picks': len(draft_results),
            'date': self.get_current_date(),
        }
        self.actions_taken.append(action)

        if self.verbose_logging:
            print(f"Draft complete: {len(draft_results)} total picks")

        return {
            'total_picks': len(draft_results),
            'picks_by_round': self._group_picks_by_round(draft_results),
            'user_team_picks': [p for p in draft_results if p['team_id'] == user_team_id],
            'notable_picks': draft_results[:32] if draft_results else [],  # Top 32 picks
        }

    def get_team_draft_picks(
        self,
        team_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get team's draft picks for current year.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of draft pick dictionaries with:
                - round: Draft round
                - pick: Pick number in round
                - overall_pick: Overall pick number
                - original_team: Team that originally owned pick
                - via_trade: Whether pick was acquired via trade
        """
        # TODO: Implement once draft pick tracking is added
        # This would query draft_picks table for team's picks

        picks = []

        if self.verbose_logging:
            print(f"Team {team_id} has {len(picks)} draft picks")

        return picks

    # ========== Public API: Roster Management Methods ==========

    def get_roster(
        self,
        team_id: int,
        include_practice_squad: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get current roster for a team.

        Args:
            team_id: Team ID (1-32)
            include_practice_squad: Include practice squad players

        Returns:
            List of player dictionaries with:
                - player_id, name, position
                - jersey_number, years_in_league
                - contract_info: Years remaining, salary
                - depth_chart_position: Starter, 2nd string, etc.
        """
        return self.roster_manager.get_roster(
            team_id=team_id,
            include_practice_squad=include_practice_squad
        )

    def cut_player(
        self,
        team_id: int,
        player_id: int,
        june_1_designation: bool = False
    ) -> Dict[str, Any]:
        """
        Cut a player from the roster.

        Calculates dead money and cap impact.

        Args:
            team_id: Team ID (1-32)
            player_id: Player to cut
            june_1_designation: Whether to designate as June 1 cut

        Returns:
            Dictionary with:
                - player_cut: True if successful
                - player_info: Cut player details
                - dead_money: Dead money cap hit
                - cap_savings: Cap space freed
                - cap_space_remaining: Team's remaining cap space
                - june_1_designation: Whether June 1 rules applied

        NFL Rules:
            - June 1 designation: Dead money spread over 2 years
            - Standard cut: All dead money in current year
            - Teams can designate 2 players for June 1 treatment pre-June 1
        """
        # Get player info
        player_info = self._get_player_info(player_id)

        # Cut player via RosterManager
        cut_result = self.roster_manager.cut_player(
            team_id=team_id,
            player_id=player_id,
            june_1_designation=june_1_designation
        )

        # Track action
        action = {
            'type': 'PLAYER_CUT',
            'team_id': team_id,
            'player_id': player_id,
            'june_1_designation': june_1_designation,
            'date': self.get_current_date(),
        }
        self.actions_taken.append(action)

        result = {
            'player_cut': True,
            'player_info': player_info,
            'dead_money': cut_result.get('dead_money', 0),
            'cap_savings': cut_result.get('cap_savings', 0),
            'cap_space_remaining': cut_result.get('cap_space_remaining', 0),
            'june_1_designation': june_1_designation,
        }

        if self.verbose_logging:
            player_name = player_info.get('name', f'Player {player_id}')
            print(f"Cut {player_name} from team {team_id}")
            print(f"  Dead money: ${result['dead_money']:,}")
            print(f"  Cap savings: ${result['cap_savings']:,}")

        return result

    def finalize_53_man_roster(self, team_id: int) -> Dict[str, Any]:
        """
        Finalize 53-man roster for start of season.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with:
                - finalized: True if successful
                - roster_size: Final roster size (should be 53)
                - cuts_needed: Players still to cut (0 if valid)
                - violations: List of rule violations if any
        """
        # Validate phase
        if self.current_phase != OffseasonPhase.ROSTER_CUTS:
            if self.verbose_logging:
                print(f"Warning: Roster cuts typically done in late August")

        # Finalize via RosterManager
        result = self.roster_manager.finalize_53_man_roster(team_id=team_id)

        if result.get('finalized'):
            action = {
                'type': 'ROSTER_FINALIZED',
                'team_id': team_id,
                'date': self.get_current_date(),
            }
            self.actions_taken.append(action)

        if self.verbose_logging:
            if result.get('finalized'):
                print(f"Team {team_id} roster finalized: {result.get('roster_size')} players")
            else:
                print(f"Team {team_id} roster not valid: {result.get('violations')}")

        return result

    # ========== Private Methods ==========

    def _detect_current_phase(self) -> OffseasonPhase:
        """
        Determine current offseason phase based on calendar date.

        Returns:
            Current OffseasonPhase
        """
        current_date = self.get_current_date()

        # Convert to datetime.date for comparison if it's not already
        if hasattr(current_date, 'to_python_date'):
            # Calendar returns custom Date object - convert to date
            current_dt = current_date.to_python_date()
        elif isinstance(current_date, datetime):
            current_dt = current_date.date()
        else:
            # Already a date object
            current_dt = current_date

        # Define phase boundaries (adjust year based on season_year)
        # Offseason is year after season
        year = self.season_year + 1

        from datetime import date

        if current_dt < date(year, 3, 1):
            return OffseasonPhase.POST_SUPER_BOWL
        elif current_dt < date(year, 3, 6):
            return OffseasonPhase.FRANCHISE_TAG_PERIOD
        elif current_dt < date(year, 3, 11):
            return OffseasonPhase.PRE_FREE_AGENCY
        elif current_dt < date(year, 3, 13):
            return OffseasonPhase.FREE_AGENCY_LEGAL_TAMPERING
        elif current_dt < date(year, 4, 24):
            return OffseasonPhase.FREE_AGENCY_OPEN
        elif current_dt < date(year, 4, 28):
            return OffseasonPhase.DRAFT
        elif current_dt < date(year, 8, 26):
            return OffseasonPhase.POST_DRAFT
        elif current_dt < date(year, 8, 30):
            return OffseasonPhase.ROSTER_CUTS
        else:
            return OffseasonPhase.COMPLETE

    def _initialize_deadlines(self) -> List[Dict[str, Any]]:
        """
        Initialize offseason deadline tracking.

        Returns:
            List of deadline dictionaries
        """
        year = self.season_year + 1
        from datetime import date

        deadlines = [
            {
                'type': 'FRANCHISE_TAG_DEADLINE',
                'date': date(year, 3, 5),  # March 5
                'description': 'Franchise tag deadline',
                'action': 'check_franchise_tags_applied'
            },
            {
                'type': 'LEGAL_TAMPERING_START',
                'date': date(year, 3, 11),  # March 11
                'description': 'Legal tampering period begins',
                'action': 'enable_free_agency_negotiations'
            },
            {
                'type': 'FREE_AGENCY_START',
                'date': date(year, 3, 13),  # March 13
                'description': 'Free agency opens',
                'action': 'enable_free_agency_signings'
            },
            {
                'type': 'DRAFT_START',
                'date': date(year, 4, 24),  # April 24
                'description': 'NFL Draft begins',
                'action': 'initialize_draft'
            },
            {
                'type': 'DRAFT_END',
                'date': date(year, 4, 27),  # April 27
                'description': 'NFL Draft concludes',
                'action': 'finalize_draft_class'
            },
            {
                'type': 'ROSTER_CUT_DEADLINE',
                'date': date(year, 8, 26),  # August 26
                'description': 'Final roster cuts to 53',
                'action': 'validate_53_man_rosters'
            },
            {
                'type': 'SEASON_START',
                'date': date(year, 9, 5),  # September 5
                'description': 'Regular season begins',
                'action': 'transition_to_season'
            }
        ]

        return deadlines

    def _check_deadlines_passed(self) -> List[str]:
        """
        Check if any deadlines were just passed.

        Returns:
            List of deadline types that were just passed
        """
        current_date = self.get_current_date()

        # Convert to date for comparison if needed
        if hasattr(current_date, 'to_python_date'):
            current_dt = current_date.to_python_date()
        elif isinstance(current_date, datetime):
            current_dt = current_date.date()
        else:
            current_dt = current_date

        passed = []

        for deadline in self.deadlines:
            # Check if deadline was just passed (not already in deadlines_passed)
            if (deadline['date'] <= current_dt and
                    deadline['type'] not in self.deadlines_passed):
                passed.append(deadline['type'])

        return passed

    def _trigger_deadline_event(self, deadline_type: str) -> Optional[Dict[str, Any]]:
        """
        Trigger automatic event for a deadline.

        Args:
            deadline_type: Type of deadline

        Returns:
            Event details if event was triggered, None otherwise
        """
        # Find deadline configuration
        deadline_config = None
        for deadline in self.deadlines:
            if deadline['type'] == deadline_type:
                deadline_config = deadline
                break

        if not deadline_config:
            return None

        # Execute deadline action
        action = deadline_config.get('action')

        if self.verbose_logging:
            print(f"Triggering deadline event: {deadline_type} ({action})")

        # TODO: Implement specific deadline actions
        # For now, just return event details
        return {
            'type': deadline_type,
            'action': action,
            'description': deadline_config.get('description'),
            'triggered_at': self.get_current_date(),
        }

    def _get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get player information from database.

        Args:
            player_id: Player ID

        Returns:
            Player info dictionary or None if not found
        """
        # TODO: Implement once player data structure is finalized
        # This should query the database for player info including:
        # - player_id, name, position, team_id
        # - contract information
        # - years_with_team
        # - accrued_seasons

        # For now, return a stub
        return {
            'player_id': player_id,
            'name': f'Player {player_id}',
            'position': 'QB',
            'team_id': None,
            'previous_salary': 0,
        }

    def _get_rfa_compensation_description(self, tender_level: str) -> str:
        """
        Get human-readable description of RFA compensation.

        Args:
            tender_level: RFA tender level

        Returns:
            Description of draft pick compensation
        """
        compensation_map = {
            'FIRST_ROUND': '1st round draft pick',
            'SECOND_ROUND': '2nd round draft pick',
            'ORIGINAL_ROUND': 'Original draft round pick',
            'RIGHT_OF_FIRST_REFUSAL': 'No draft pick compensation',
        }
        return compensation_map.get(tender_level, 'Unknown')

    def _group_picks_by_round(self, picks: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Group draft picks by round.

        Args:
            picks: List of draft pick dictionaries

        Returns:
            Dictionary mapping round number to list of picks in that round
        """
        picks_by_round = {}

        for pick in picks:
            round_num = pick.get('round', 1)
            if round_num not in picks_by_round:
                picks_by_round[round_num] = []
            picks_by_round[round_num].append(pick)

        return picks_by_round

    # ========== Public API: AI Offseason Simulation ==========

    def simulate_ai_full_offseason(self, user_team_id: int) -> Dict[str, Any]:
        """
        Simulate complete AI offseason for all non-user teams.

        Executes:
        1. Franchise tags for all AI teams
        2. 30-day free agency simulation
        3. Roster cuts (90 → 53) for all teams

        Args:
            user_team_id: User's team ID (will be skipped)

        Returns:
            Dictionary with:
                - franchise_tags_applied: Number of tags applied
                - free_agent_signings: Number of FA signings
                - roster_cuts_made: Number of cuts across all teams
                - total_transactions: Total transaction count
                - summary_by_team: Per-team transaction breakdown
        """
        ai_teams = [t for t in range(1, 33) if t != user_team_id]

        franchise_tags_count = 0
        fa_signings_count = 0
        roster_cuts_count = 0

        if self.verbose_logging:
            print("\n" + "=" * 80)
            print("  AI OFFSEASON SIMULATION")
            print("=" * 80)
            print(f"Simulating offseason for {len(ai_teams)} AI teams...")
            print()

        # Step 1: Franchise Tag Period (all AI teams)
        if self.verbose_logging:
            print("STEP 1: Franchise Tags")
            print("-" * 80)

        for team_id in ai_teams:
            try:
                # Get tag candidates
                candidates = self.get_franchise_tag_candidates(team_id)

                # AI applies tag to top candidate if available
                if candidates:
                    top_candidate = candidates[0]
                    if top_candidate['recommendation'] == 'TAG':
                        # Apply franchise tag
                        result = self.apply_franchise_tag(
                            player_id=top_candidate['player_id'],
                            team_id=team_id,
                            tag_type="NON_EXCLUSIVE"
                        )
                        franchise_tags_count += 1

                        if self.verbose_logging:
                            print(f"  Team {team_id}: Tagged {top_candidate['player_name']} "
                                  f"({top_candidate['position']}) - ${result['tag_salary']:,}")
            except Exception as e:
                self.logger.error(f"Error applying franchise tag for team {team_id}: {e}")
                continue

        if self.verbose_logging:
            print(f"\n✅ Applied {franchise_tags_count} franchise tags\n")

        # Step 2: Free Agency (30-day simulation)
        if self.verbose_logging:
            print("STEP 2: Free Agency")
            print("-" * 80)

        try:
            fa_signings = self.simulate_ai_free_agency(
                user_team_id=user_team_id,
                days_to_simulate=30
            )
            fa_signings_count = len(fa_signings)

            if self.verbose_logging:
                print(f"✅ AI teams made {fa_signings_count} free agent signings\n")
        except Exception as e:
            self.logger.error(f"Error in free agency simulation: {e}")

        # Step 3: Roster Cuts (90 → 53)
        if self.verbose_logging:
            print("STEP 3: Roster Cuts")
            print("-" * 80)

        for team_id in ai_teams:
            try:
                # AI performs roster cuts
                cut_result = self.roster_manager.finalize_53_man_roster_ai(team_id)

                cuts_made = cut_result.get('total_cut', 0)
                roster_cuts_count += cuts_made

                if self.verbose_logging and cuts_made > 0:
                    print(f"  Team {team_id}: Cut {cuts_made} players (90 → 53)")
            except Exception as e:
                self.logger.error(f"Error in roster cuts for team {team_id}: {e}")
                continue

        if self.verbose_logging:
            print(f"\n✅ Made {roster_cuts_count} roster cuts across all teams\n")

        # Summary
        total_transactions = franchise_tags_count + fa_signings_count + roster_cuts_count

        result = {
            'franchise_tags_applied': franchise_tags_count,
            'free_agent_signings': fa_signings_count,
            'roster_cuts_made': roster_cuts_count,
            'total_transactions': total_transactions,
            'ai_teams_processed': len(ai_teams)
        }

        if self.verbose_logging:
            print("=" * 80)
            print("  OFFSEASON SIMULATION COMPLETE")
            print("=" * 80)
            print(f"  Total Transactions: {total_transactions}")
            print(f"  - Franchise Tags: {franchise_tags_count}")
            print(f"  - Free Agency: {fa_signings_count}")
            print(f"  - Roster Cuts: {roster_cuts_count}")
            print("=" * 80)
            print()

        return result
