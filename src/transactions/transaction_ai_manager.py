"""
Transaction AI Manager

Central orchestrator for AI-driven in-season transactions.
Coordinates daily trade evaluation for all 32 NFL teams using GM archetypes,
team needs, and season context.

Phase 1.5 of AI Transaction System implementation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import random
import logging

from transactions.trade_proposal_generator import TradeProposalGenerator, TeamContext
from transactions.trade_value_calculator import TradeValueCalculator
from transactions.trade_evaluator import TradeEvaluator
from transactions.models import TradeProposal, TradeDecision, TradeDecisionType, AssetType
from team_management.gm_archetype import GMArchetype
from offseason.team_needs_analyzer import TeamNeedsAnalyzer
from salary_cap.cap_database_api import CapDatabaseAPI
from calendar.season_phase_tracker import SeasonPhase


# Configuration Constants
BASE_EVALUATION_PROBABILITY = 0.05  # 5% per day baseline
MAX_TRANSACTIONS_PER_DAY = 2  # Maximum proposals per team per day
TRADE_COOLDOWN_DAYS = 7  # Days after trade before next evaluation
TRADE_DEADLINE_WEEK = 8  # NFL trade deadline (Week 8 Tuesday)

# Probability Modifiers
MODIFIER_PLAYOFF_PUSH = 1.5  # +50% if in wild card hunt (weeks 10+)
MODIFIER_LOSING_STREAK = 1.25  # +25% per game in 3+ game losing streak
MODIFIER_INJURY_EMERGENCY = 3.0  # +200% if critical starter injured
MODIFIER_POST_TRADE_COOLDOWN = 0.2  # -80% for 7 days after trade
MODIFIER_DEADLINE_PROXIMITY = 2.0  # +100% in final 3 days before deadline

# GM Philosophy Filter Thresholds
STAR_CHASING_HIGH = 0.6  # Above this: prefer 85+ OVR
STAR_CHASING_LOW = 0.4  # Below this: avoid 88+ OVR
VETERAN_PREF_HIGH = 0.7  # Above this: prefer age 27+
VETERAN_PREF_LOW = 0.3  # Below this: prefer age <29
DRAFT_PICK_VALUE_HIGH = 0.6  # Above this: reluctant to trade picks
CAP_MGMT_HIGH = 0.7  # Above this: max 50% cap consumption
CAP_MGMT_MEDIUM = 0.4  # 0.4-0.7: max 70% cap consumption
LOYALTY_HIGH = 0.7  # Above this: avoid trading 5+ year veterans
WIN_NOW_HIGH = 0.7  # Above this: prefer proven talent over picks
REBUILD_LOW = 0.3  # Below this: prefer picks/youth over veterans


@dataclass
class TransactionAIManager:
    """
    Central orchestrator for AI-driven in-season transactions.

    Coordinates daily trade evaluation for all 32 NFL teams using
    GM archetypes, team needs, and season context.

    Attributes:
        database_path: Path to SQLite database
        dynasty_id: Dynasty identifier for isolation
        calculator: Trade value calculator instance
        proposal_generator: Trade proposal generator instance
        base_evaluation_probability: Base daily evaluation probability (default: 0.05)
        max_transactions_per_day: Max proposals per team per day (default: 2)
        trade_cooldown_days: Days before re-evaluation after trade (default: 7)
        debug_mode: Enable comprehensive debug logging (default: False)
    """

    database_path: str
    dynasty_id: str

    # Component instances (will be created in __post_init__ if not provided)
    calculator: Optional[TradeValueCalculator] = None
    proposal_generator: Optional[TradeProposalGenerator] = None
    needs_analyzer: Optional[TeamNeedsAnalyzer] = None
    cap_api: Optional[CapDatabaseAPI] = None

    # Configuration
    base_evaluation_probability: float = BASE_EVALUATION_PROBABILITY
    max_transactions_per_day: int = MAX_TRANSACTIONS_PER_DAY
    trade_cooldown_days: int = TRADE_COOLDOWN_DAYS
    debug_mode: bool = False

    # Trade history tracking (team_id -> last_trade_date)
    _trade_history: Dict[int, str] = field(default_factory=dict)

    # Performance metrics
    _evaluation_count: int = field(default=0, init=False)
    _proposal_count: int = field(default=0, init=False)
    _total_evaluation_time_ms: float = field(default=0.0, init=False)

    # Debug data collection
    _debug_data: List[Dict[str, Any]] = field(default_factory=list, init=False)

    # Logger
    logger: Optional[logging.Logger] = field(default=None, init=False)

    def __post_init__(self):
        """Initialize components if not provided."""
        # Initialize logger
        self.logger = logging.getLogger("TransactionAIManager")

        if self.calculator is None:
            from database.player_roster_api import PlayerRosterAPI
            player_api = PlayerRosterAPI(self.database_path)
            self.calculator = TradeValueCalculator(
                current_year=2025,  # TODO: Get from season context
                dynasty_id=self.dynasty_id,
                player_roster_api=player_api,
                team_needs_analyzer=self.needs_analyzer
            )

        if self.proposal_generator is None:
            self.proposal_generator = TradeProposalGenerator(
                self.database_path,
                self.dynasty_id,
                self.calculator,
                debug_mode=self.debug_mode  # Pass debug mode to generator
            )

        if self.needs_analyzer is None:
            self.needs_analyzer = TeamNeedsAnalyzer(self.database_path, self.dynasty_id)

        if self.cap_api is None:
            self.cap_api = CapDatabaseAPI(self.database_path)

        # Load trade history from database (if available)
        self._load_trade_history()

        if self.debug_mode:
            self.logger.info("[DEBUG_MODE] TransactionAIManager initialized in debug mode")

    def _load_trade_history(self) -> None:
        """
        Load recent trade history from database for cooldown tracking.

        Placeholder for now - will integrate with transaction history table.
        """
        # TODO: Query database for last trade date per team
        # For now, initialize empty history
        self._trade_history = {}

    # -------------------------------------------------------------------------
    # Probability System
    # -------------------------------------------------------------------------

    def _should_evaluate_today(
        self,
        team_id: int,
        gm: GMArchetype,
        team_context: TeamContext,
        season_phase: SeasonPhase,
        current_date: str,
        current_week: int = 1
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Determine if team should evaluate trades today.

        Most days return False (realistic NFL behavior).

        Base Probability: gm.trade_frequency * base_evaluation_probability
        - trade_frequency=0.5, base=0.05 → 2.5% per day
        - Over 120 days: ~3 evaluations per season

        Modifiers:
        - Playoff push: +50% if in wild card hunt (weeks 10+)
        - Losing streak: +25% per game in 3+ game losing streak
        - Injury emergency: +200% if starter injured at critical position
        - Post-trade cooldown: -80% for 7 days after trade
        - Trade deadline proximity: +100% in final 3 days before deadline

        Args:
            team_id: NFL team ID (1-32)
            gm: GM archetype for personality traits
            team_context: Current team state (wins, losses, cap space)
            season_phase: SeasonPhase enum (PRESEASON, REGULAR_SEASON, PLAYOFFS, OFFSEASON)
            current_date: Current date string (YYYY-MM-DD)
            current_week: Current week number (1-18)

        Returns:
            Tuple of (decision, debug_data):
            - decision: True if team should evaluate today (rare), False otherwise
            - debug_data: Debug information if debug_mode enabled, None otherwise
        """
        # Initialize debug data collection
        debug_data = {} if self.debug_mode else None

        # Allow evaluation during preseason, regular season, and offseason (trades blocked by specific deadlines)
        if season_phase not in [SeasonPhase.PRESEASON, SeasonPhase.REGULAR_SEASON, SeasonPhase.OFFSEASON]:
            if self.debug_mode:
                debug_data['decision'] = 'NO_EVALUATE'
                debug_data['reason'] = f'Trades only during preseason/regular/offseason (current={season_phase.value})'
            return False, debug_data

        # Check trade deadline (Week 8 Tuesday - no trades AFTER deadline week)
        # Allow trades through the end of Week 8, block starting Week 9
        if current_week > TRADE_DEADLINE_WEEK:
            if self.debug_mode:
                debug_data['decision'] = 'NO_EVALUATE'
                debug_data['reason'] = f'After trade deadline (week {current_week} > {TRADE_DEADLINE_WEEK})'
            return False, debug_data

        # Calculate base probability
        base_prob = gm.trade_frequency * self.base_evaluation_probability

        if self.debug_mode:
            debug_data['base_prob'] = base_prob
            debug_data['gm_trade_frequency'] = gm.trade_frequency
            debug_data['system_base_prob'] = self.base_evaluation_probability
            debug_data['modifiers'] = {}

        # Apply modifiers
        modifier = 1.0

        # 1. Playoff push modifier (weeks 10+)
        is_playoff_push = False
        if current_week >= 10:
            if self._is_in_playoff_hunt(team_context):
                modifier *= MODIFIER_PLAYOFF_PUSH
                is_playoff_push = True
                if self.debug_mode:
                    debug_data['modifiers']['playoff_push'] = {
                        'applied': True,
                        'value': MODIFIER_PLAYOFF_PUSH,
                        'reason': f'In playoff hunt (week {current_week})'
                    }
        if self.debug_mode and not is_playoff_push:
            debug_data['modifiers']['playoff_push'] = {'applied': False, 'value': 1.0}

        # 2. Losing streak modifier
        losing_streak_games = self._get_losing_streak_length(team_context)
        if losing_streak_games >= 3:
            # +25% per game in streak
            streak_modifier = MODIFIER_LOSING_STREAK ** (losing_streak_games - 2)
            modifier *= streak_modifier
            if self.debug_mode:
                debug_data['modifiers']['losing_streak'] = {
                    'applied': True,
                    'value': streak_modifier,
                    'reason': f'{losing_streak_games} game losing streak'
                }
        elif self.debug_mode:
            debug_data['modifiers']['losing_streak'] = {'applied': False, 'value': 1.0}

        # 3. Injury emergency modifier (placeholder - needs injury data)
        if self.debug_mode:
            debug_data['modifiers']['injury_emergency'] = {'applied': False, 'value': 1.0, 'reason': 'Not implemented'}

        # 4. Post-trade cooldown modifier
        is_cooldown = self._is_in_trade_cooldown(team_id, current_date)
        if is_cooldown:
            modifier *= MODIFIER_POST_TRADE_COOLDOWN
            if self.debug_mode:
                debug_data['modifiers']['cooldown'] = {
                    'applied': True,
                    'value': MODIFIER_POST_TRADE_COOLDOWN,
                    'reason': f'Recent trade (cooldown: {self.trade_cooldown_days} days)'
                }
        elif self.debug_mode:
            debug_data['modifiers']['cooldown'] = {'applied': False, 'value': 1.0}

        # 5. Trade deadline proximity (final 3 days before deadline)
        is_near_deadline = self._is_near_trade_deadline(current_week, current_date)
        if is_near_deadline:
            modifier *= MODIFIER_DEADLINE_PROXIMITY
            if self.debug_mode:
                debug_data['modifiers']['deadline_proximity'] = {
                    'applied': True,
                    'value': MODIFIER_DEADLINE_PROXIMITY,
                    'reason': 'Within 3 days of trade deadline'
                }
        elif self.debug_mode:
            debug_data['modifiers']['deadline_proximity'] = {'applied': False, 'value': 1.0}

        # Calculate final probability
        final_prob = min(base_prob * modifier, 1.0)  # Cap at 100%

        # Random check
        random_roll = random.random()
        decision = random_roll < final_prob

        if self.debug_mode:
            debug_data['final_prob'] = final_prob
            debug_data['total_modifier'] = modifier
            debug_data['random_roll'] = random_roll
            debug_data['decision'] = 'EVALUATE' if decision else 'NO_EVALUATE'
            if decision:
                debug_data['reason'] = f'Random roll ({random_roll:.3f}) < final probability ({final_prob:.3f})'
            else:
                debug_data['reason'] = f'Random roll ({random_roll:.3f}) >= final probability ({final_prob:.3f})'

        return decision, debug_data

    def _is_in_playoff_hunt(self, team_context: TeamContext) -> bool:
        """
        Check if team is in wild card hunt (close to playoff cutoff).

        Simplified check: win percentage between 0.40 and 0.60
        (marginal teams more likely to make moves)

        Args:
            team_context: Current team state

        Returns:
            True if team is in wild card hunt
        """
        total_games = team_context.wins + team_context.losses
        if total_games == 0:
            return False

        win_pct = team_context.wins / total_games
        return 0.40 <= win_pct <= 0.60

    def _get_losing_streak_length(self, team_context: TeamContext) -> int:
        """
        Get length of current losing streak.

        Placeholder: Would need game-by-game history to calculate accurately.
        For now, infer from overall record (if losses > wins, assume streak).

        Args:
            team_context: Current team state

        Returns:
            Estimated losing streak length (0 if winning)
        """
        # Placeholder logic: if team has 3+ more losses than wins, assume 3-game streak
        loss_differential = team_context.losses - team_context.wins
        if loss_differential >= 3:
            return 3  # Conservative estimate
        return 0

    def _is_in_trade_cooldown(self, team_id: int, current_date: str) -> bool:
        """
        Check if team is in post-trade cooldown period.

        Args:
            team_id: NFL team ID
            current_date: Current date string (YYYY-MM-DD)

        Returns:
            True if within TRADE_COOLDOWN_DAYS of last trade
        """
        if team_id not in self._trade_history:
            return False

        last_trade_date_str = self._trade_history[team_id]
        try:
            last_trade_date = datetime.fromisoformat(last_trade_date_str)
            current_date_obj = datetime.fromisoformat(current_date)
            days_since_trade = (current_date_obj - last_trade_date).days
            return days_since_trade < self.trade_cooldown_days
        except ValueError:
            # Invalid date format, assume not in cooldown
            return False

    def _is_near_trade_deadline(self, current_week: int, current_date: str) -> bool:
        """
        Check if within 3 days of trade deadline.

        Trade deadline: Week 8 Tuesday

        Args:
            current_week: Current week number (1-18)
            current_date: Current date string (YYYY-MM-DD)

        Returns:
            True if within 3 days before deadline
        """
        # Simple check: if Week 8, assume within deadline proximity
        # More sophisticated implementation would check actual date
        return current_week == TRADE_DEADLINE_WEEK


    def _get_days_since_last_trade(self, team_id: int, current_date: str) -> Optional[int]:
        """
        Get number of days since team's last trade.

        Returns None if no trade history exists.

        Args:
            team_id: NFL team ID (1-32)
            current_date: Current date string (YYYY-MM-DD)

        Returns:
            Number of days since last trade, or None if no history
        """
        if team_id not in self._trade_history:
            return None

        last_trade_date_str = self._trade_history[team_id]
        try:
            last_trade_date = datetime.fromisoformat(last_trade_date_str)
            current_date_obj = datetime.fromisoformat(current_date)
            days_since = (current_date_obj - last_trade_date).days
            return days_since
        except ValueError:
            # Invalid date format
            return None

    def _calculate_desperation_level(
        self,
        team_context: TeamContext,
        gm: GMArchetype
    ) -> float:
        """
        Calculate team's desperation level (0.0-1.0).

        Factors:
        - Losing streak length (from team_context)
        - Distance from playoff cutoff (0.500 win%)
        - GM's desperation_threshold trait (via win_now_mentality)

        Returns 0.0 = content, 1.0 = desperate

        Args:
            team_context: Current team state (wins, losses)
            gm: GM archetype for desperation threshold

        Returns:
            Desperation level from 0.0 (content) to 1.0 (desperate)
        """
        # Calculate win percentage
        total_games = team_context.wins + team_context.losses
        if total_games == 0:
            return 0.0  # Season start, no desperation yet

        win_pct = team_context.wins / total_games

        # Distance from playoff cutoff (0.500)
        playoff_cutoff = 0.500
        distance_from_cutoff = abs(win_pct - playoff_cutoff)

        # Base desperation from record (0.0-0.5 range)
        # Teams far from .500 are more desperate (either to rebuild or win now)
        record_desperation = min(distance_from_cutoff * 2.0, 0.5)

        # Losing streak factor (0.0-0.3 range)
        losing_streak = self._get_losing_streak_length(team_context)
        streak_desperation = 0.0
        if losing_streak >= 3:
            # 3-game: 0.1, 4-game: 0.2, 5+: 0.3
            streak_desperation = min((losing_streak - 2) * 0.1, 0.3)

        # GM personality factor (0.0-0.2 range)
        # High win_now_mentality = more desperate when losing
        # Low win_now_mentality = less desperate (patient rebuild)
        if win_pct < playoff_cutoff:
            # Losing teams: win_now GMs get more desperate
            gm_factor = gm.win_now_mentality * 0.2
        else:
            # Winning teams: not as desperate regardless of GM
            gm_factor = 0.0

        # Combine factors (max 1.0)
        total_desperation = min(
            record_desperation + streak_desperation + gm_factor,
            1.0
        )

        return total_desperation

    def _has_critical_injury(self, team_id: int) -> bool:
        """
        Check if team has critical starter injury.

        Placeholder for future injury system integration.
        Returns False for now.

        Args:
            team_id: NFL team ID (1-32)

        Returns:
            False (placeholder - no injury system yet)
        """
        return False

    # -------------------------------------------------------------------------
    # Placeholder Methods (Will be implemented in Days 2-5)
    # -------------------------------------------------------------------------

    def evaluate_daily_transactions(
        self,
        team_id: int,
        current_date: str,
        season_phase: str,
        team_record: Dict[str, int],
        current_week: int = 1
    ) -> Tuple[List[TradeProposal], Optional[Dict[str, Any]]]:
        """
        Daily transaction evaluation for one team.

        Returns 0-2 trade proposals to execute today.

        Pipeline:
        1. Probability check - should_evaluate_today()
        2. Team assessment - assess team needs, cap space, GM archetype
        3. Proposal generation - generate_trade_proposals()
        4. GM philosophy filter - filter by personality traits (Day 3)
        5. Validation - cap compliance, roster minimums (Day 3)
        6. Prioritization - sort by urgency and fairness

        Args:
            team_id: NFL team ID (1-32)
            current_date: Current date (YYYY-MM-DD)
            season_phase: "preseason", "regular", "playoffs"
            team_record: {"wins": int, "losses": int, "ties": int}
            current_week: Current week number (1-18)

        Returns:
            Tuple of (proposals, debug_data):
            - proposals: List of 0-2 trade proposals (most days: empty list)
            - debug_data: Debug information if debug_mode enabled, None otherwise
        """
        start_time = datetime.now()

        # Initialize debug data
        debug_data = {'team_id': team_id} if self.debug_mode else None

        try:
            # Step 1: Assess team situation
            team_needs, cap_space, gm_archetype, team_context = self._assess_team_situation(
                team_id, team_record
            )

            if self.debug_mode:
                debug_data['team_needs_count'] = len(team_needs)
                debug_data['cap_space'] = cap_space

            # Step 2: Probability check - should we evaluate today?
            should_evaluate, prob_debug = self._should_evaluate_today(
                team_id, gm_archetype, team_context, season_phase, current_date, current_week
            )

            if self.debug_mode:
                debug_data['probability_check'] = prob_debug

            if not should_evaluate:
                self._evaluation_count += 1
                if self.debug_mode:
                    debug_data['proposals_generated'] = 0
                    debug_data['proposals_accepted'] = 0
                    # Store debug data before early return
                    self._debug_data.append(debug_data)
                return [], debug_data  # Most days return empty (realistic)

            # Step 3: Check if we have any needs to address
            if not team_needs:
                self._evaluation_count += 1
                if self.debug_mode:
                    debug_data['proposals_generated'] = 0
                    debug_data['proposals_accepted'] = 0
                    debug_data['early_exit_reason'] = 'No team needs'
                    # Store debug data before early return
                    self._debug_data.append(debug_data)
                return [], debug_data  # No needs, no trades

            # Step 4: Generate trade proposals
            if self.debug_mode:
                proposals, proposal_debug = self.proposal_generator.generate_trade_proposals(
                    team_id=team_id,
                    gm_archetype=gm_archetype,
                    team_context=team_context,
                    needs=team_needs,
                    season=2025  # TODO: Make year configurable
                )
                debug_data['proposal_generation'] = proposal_debug
            else:
                proposals = self.proposal_generator.generate_trade_proposals(
                    team_id=team_id,
                    gm_archetype=gm_archetype,
                    team_context=team_context,
                    needs=team_needs,
                    season=2025
                )

            proposals_generated = len(proposals)
            self._proposal_count += proposals_generated

            if self.debug_mode:
                debug_data['proposals_generated'] = proposals_generated
                debug_data['proposals'] = []

            # Step 5: GM philosophy filtering (Day 3 - IMPLEMENTED)
            proposals_before_gm_filter = len(proposals)
            proposals = self._filter_by_gm_philosophy(proposals, gm_archetype, team_context)

            if self.debug_mode:
                debug_data['gm_filter_passed'] = len(proposals)
                debug_data['gm_filter_rejected'] = proposals_before_gm_filter - len(proposals)

            # Step 6: Validation (Day 3 - IMPLEMENTED)
            proposals_before_validation = len(proposals)
            proposals = self._validate_proposals(proposals, team_id)

            if self.debug_mode:
                debug_data['validation_passed'] = len(proposals)
                debug_data['validation_rejected'] = proposals_before_validation - len(proposals)

            # Step 7: Prioritization - sort by urgency and fairness
            proposals = self._prioritize_proposals(proposals, team_needs, gm_archetype)

            # Step 8: Limit to max transactions per day
            final_proposals = proposals[:self.max_transactions_per_day]

            if self.debug_mode:
                debug_data['proposals_accepted'] = len(final_proposals)

            self._evaluation_count += 1

            # Log evaluation metrics
            elapsed_time = (datetime.now() - start_time).total_seconds() * 1000
            self._log_evaluation_metrics(
                team_id=team_id,
                evaluation_time_ms=elapsed_time,
                proposals_generated=proposals_generated,
                proposals_accepted=len(final_proposals)
            )

            if self.debug_mode:
                debug_data['evaluation_time_ms'] = elapsed_time
                # Store debug data in manager's collection for UI access
                self._debug_data.append(debug_data)

            return final_proposals, debug_data

        finally:
            # Track performance metrics
            elapsed_time = (datetime.now() - start_time).total_seconds() * 1000
            self._total_evaluation_time_ms += elapsed_time

    def _assess_team_situation(
        self,
        team_id: int,
        team_record: Dict[str, int]
    ) -> Tuple[List[Dict], int, GMArchetype, TeamContext]:
        """
        Assess team's current situation for trade evaluation.

        Uses existing systems to gather:
        - Team needs (via TeamNeedsAnalyzer)
        - Cap space (via CapDatabaseAPI)
        - GM archetype (placeholder - will use GMArchetypeFactory)
        - Team context (constructed from team_record)

        Args:
            team_id: NFL team ID (1-32)
            team_record: {"wins": int, "losses": int, "ties": int}

        Returns:
            Tuple of (team_needs, cap_space, gm_archetype, team_context)
        """
        # 1. Analyze team needs
        team_needs = self.needs_analyzer.analyze_team_needs(team_id, 2025)  # TODO: Make season configurable

        # 2. Get cap space
        # Note: For demo purposes, use mock cap space if database doesn't have data
        try:
            # Try new method if it exists (for testing)
            if hasattr(self.cap_api, 'get_available_cap_space') and callable(self.cap_api.get_available_cap_space):
                cap_space = self.cap_api.get_available_cap_space(team_id)
                # Ensure it's an integer, not a Mock
                if not isinstance(cap_space, int):
                    cap_space = 50_000_000
            else:
                # Use standard method
                cap_summary = self.cap_api.get_team_cap_summary(team_id, 2025, self.dynasty_id)
                if cap_summary and isinstance(cap_summary, dict):
                    cap_space = cap_summary.get('available_space', 50_000_000)
                else:
                    cap_space = 50_000_000
        except:
            # Fallback to mock data for demo
            cap_space = 50_000_000  # $50M default

        # 3. Get GM archetype (placeholder - create balanced GM for now)
        # TODO: Use GMArchetypeFactory to load team-specific GM
        gm_archetype = self._get_default_gm_archetype(team_id)

        # 4. Construct team context
        team_context = TeamContext(
            team_id=team_id,
            wins=team_record.get("wins", 0),
            losses=team_record.get("losses", 0),
            cap_space=cap_space,
            season="regular"  # Phase 1.5 scope
        )

        return team_needs, cap_space, gm_archetype, team_context

    def _get_default_gm_archetype(self, team_id: int) -> GMArchetype:
        """
        Get GM archetype for team.

        Placeholder: Returns balanced archetype.
        TODO: Integrate with GMArchetypeFactory for team-specific GMs.

        Args:
            team_id: NFL team ID (1-32)

        Returns:
            GMArchetype instance
        """
        from team_management.gm_archetype import GMArchetype

        # Create balanced GM as default (all traits 0.5)
        return GMArchetype(
            name=f"Team {team_id} GM",
            description="Balanced general manager",
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.5,
            star_chasing=0.5,
            loyalty=0.5
        )

    def _prioritize_proposals(
        self,
        proposals: List[TradeProposal],
        team_needs: List[Dict],
        gm_archetype: GMArchetype
    ) -> List[TradeProposal]:
        """
        Prioritize proposals by urgency and fairness.

        Sorting Priority:
        1. Addresses CRITICAL need (highest priority)
        2. Addresses HIGH need
        3. Better value ratio (closer to 1.0)
        4. Simpler trade (fewer assets)

        Args:
            proposals: List of trade proposals
            team_needs: Team position needs with urgency levels
            gm_archetype: GM personality for tie-breaking

        Returns:
            Sorted list of proposals (highest priority first)
        """
        if not proposals:
            return []

        # Create need urgency lookup (position -> urgency_value)
        need_urgency_map = {}
        for need in team_needs:
            position = need.get("position", "")
            urgency = need.get("urgency", None)

            # Map urgency to numeric value (higher = more urgent)
            if urgency:
                urgency_name = urgency.name if hasattr(urgency, 'name') else str(urgency)
                urgency_value = {
                    "CRITICAL": 4,
                    "HIGH": 3,
                    "MEDIUM": 2,
                    "LOW": 1,
                    "NONE": 0
                }.get(urgency_name, 0)
                need_urgency_map[position] = urgency_value

        def proposal_score(proposal: TradeProposal) -> Tuple[int, float, int]:
            """
            Calculate proposal priority score.

            Returns tuple for sorting: (urgency, fairness, simplicity)
            - Higher urgency = better
            - Fairness closer to 1.0 = better
            - Fewer assets = better (simpler)
            """
            # Urgency: check if proposal addresses high-urgency need
            max_urgency = 0
            for asset in proposal.team2_assets:  # Assets team is receiving
                position = asset.position.lower() if asset.position else ""
                urgency = need_urgency_map.get(position, 0)
                max_urgency = max(max_urgency, urgency)

            # Fairness: distance from 1.0 (lower is better)
            fairness_distance = abs(1.0 - proposal.value_ratio)

            # Simplicity: total asset count (lower is better)
            total_assets = len(proposal.team1_assets) + len(proposal.team2_assets)

            # Return tuple for sorting (negatives for descending order)
            return (
                -max_urgency,        # Higher urgency first (negate for sort)
                fairness_distance,   # Better fairness first (already ascending)
                total_assets         # Simpler trades first (already ascending)
            )

        # Sort proposals by score
        sorted_proposals = sorted(proposals, key=proposal_score)
        return sorted_proposals

    def _filter_by_gm_philosophy(
        self,
        proposals: List[TradeProposal],
        gm: GMArchetype,
        team_context: TeamContext
    ) -> List[TradeProposal]:
        """
        Filter trade proposals based on GM's personality and philosophy.

        Applies 6 personality-based filters to remove proposals that conflict
        with GM's management style, risk tolerance, and strategic preferences.

        Filters Applied:
        1. Star Chasing: Filter based on preference for elite talent vs cost control
        2. Veteran Preference: Filter by age preferences (veterans vs youth)
        3. Draft Pick Value: Filter pick trades based on future value (placeholder)
        4. Cap Management: Enforce cap consumption limits based on fiscal discipline
        5. Loyalty: Avoid trading long-tenured players (placeholder - needs tenure data)
        6. Win-Now vs Rebuild: Filter by proven talent vs youth development focus

        Args:
            proposals: List of trade proposals to filter
            gm: GM archetype with personality traits (0.0-1.0 scales)
            team_context: Current team state (cap space, record)

        Returns:
            Filtered list of proposals that align with GM philosophy
        """
        if not proposals:
            return []

        filtered = []

        for proposal in proposals:
            # Track if proposal passes all filters
            passes_filters = True

            # Get assets the team is acquiring (from other team)
            acquiring_assets = proposal.team2_assets if proposal.team1_id == team_context.team_id else proposal.team1_assets

            # -------------------------------------------------------------------------
            # Filter 1: Star Chasing (preference for elite talent vs cost control)
            # -------------------------------------------------------------------------
            if gm.star_chasing > STAR_CHASING_HIGH:
                # High star chasing: Prefer acquiring 85+ OVR players
                has_star = False
                for asset in acquiring_assets:
                    if asset.asset_type == AssetType.PLAYER and asset.overall_rating:
                        if asset.overall_rating >= 85:
                            has_star = True
                            break

                # If no star player in acquisition, filter out
                if not has_star:
                    passes_filters = False

            elif gm.star_chasing < STAR_CHASING_LOW:
                # Low star chasing: Avoid acquiring 88+ OVR (too expensive)
                has_expensive_star = False
                for asset in acquiring_assets:
                    if asset.asset_type == AssetType.PLAYER and asset.overall_rating:
                        if asset.overall_rating >= 88:
                            has_expensive_star = True
                            break

                # If acquiring expensive star, filter out
                if has_expensive_star:
                    passes_filters = False

            # -------------------------------------------------------------------------
            # Filter 2: Veteran Preference (age-based filtering)
            # -------------------------------------------------------------------------
            if gm.veteran_preference > VETERAN_PREF_HIGH:
                # High veteran preference: Prefer age 27+ players
                has_veteran = False
                for asset in acquiring_assets:
                    if asset.asset_type == AssetType.PLAYER and asset.age:
                        if asset.age >= 27:
                            has_veteran = True
                            break

                # If no veteran in acquisition, filter out
                if not has_veteran:
                    passes_filters = False

            elif gm.veteran_preference < VETERAN_PREF_LOW:
                # Low veteran preference: Prefer age <29 players (younger talent)
                has_old_player = False
                for asset in acquiring_assets:
                    if asset.asset_type == AssetType.PLAYER and asset.age:
                        if asset.age >= 29:
                            has_old_player = True
                            break

                # If acquiring old player, filter out
                if has_old_player:
                    passes_filters = False

            # -------------------------------------------------------------------------
            # Filter 3: Draft Pick Value (reluctance to trade future picks)
            # -------------------------------------------------------------------------
            # Phase 1.5: Placeholder - no draft pick system yet
            # Future implementation: Check if trading away future picks
            if gm.draft_pick_value > DRAFT_PICK_VALUE_HIGH:
                # High pick value: Reluctant to trade away future picks
                # TODO: When draft pick system added, check if giving up picks
                pass

            # -------------------------------------------------------------------------
            # Filter 4: Cap Management (cap consumption limits)
            # -------------------------------------------------------------------------
            # Calculate total cap hit of acquiring assets
            total_cap_hit = 0
            for asset in acquiring_assets:
                if asset.asset_type == AssetType.PLAYER and asset.annual_cap_hit:
                    total_cap_hit += asset.annual_cap_hit

            # Determine max allowed cap consumption based on GM's cap management trait
            if gm.cap_management > CAP_MGMT_HIGH:
                # Conservative: Max 50% of available cap space
                max_cap_consumption = team_context.cap_space * 0.50
            elif gm.cap_management >= CAP_MGMT_MEDIUM:
                # Moderate: Max 70% of available cap space
                max_cap_consumption = team_context.cap_space * 0.70
            else:
                # Aggressive: Max 80% of available cap space
                max_cap_consumption = team_context.cap_space * 0.80

            # Filter out if cap hit exceeds limit
            if total_cap_hit > max_cap_consumption:
                passes_filters = False

            # -------------------------------------------------------------------------
            # Filter 5: Loyalty (avoid trading long-tenured players)
            # -------------------------------------------------------------------------
            # Phase 1.5: Placeholder - need player tenure data
            # Future implementation: Check if trading away 5+ year veterans
            if gm.loyalty > LOYALTY_HIGH:
                # High loyalty: Avoid trading players with 5+ years on team
                # TODO: When tenure tracking added, check years_with_team
                pass

            # -------------------------------------------------------------------------
            # Filter 6: Win-Now vs Rebuild (proven talent vs youth)
            # -------------------------------------------------------------------------
            if gm.win_now_mentality > WIN_NOW_HIGH:
                # Win-now mode: Prefer proven talent over youth
                # Reject trades that acquire too many young/unproven players
                young_player_count = 0
                total_player_count = 0

                for asset in acquiring_assets:
                    if asset.asset_type == AssetType.PLAYER:
                        total_player_count += 1
                        if asset.age and asset.age < 27:
                            young_player_count += 1

                # If majority are young players, filter out (not win-now aligned)
                if total_player_count > 0:
                    young_ratio = young_player_count / total_player_count
                    if young_ratio > 0.6:  # >60% young players
                        passes_filters = False

            elif gm.win_now_mentality < REBUILD_LOW:
                # Rebuild mode: Prefer youth (<27) over veterans
                # Reject trades that acquire too many veterans
                veteran_count = 0
                total_player_count = 0

                for asset in acquiring_assets:
                    if asset.asset_type == AssetType.PLAYER:
                        total_player_count += 1
                        if asset.age and asset.age >= 27:
                            veteran_count += 1

                # If majority are veterans, filter out (not rebuild aligned)
                if total_player_count > 0:
                    veteran_ratio = veteran_count / total_player_count
                    if veteran_ratio > 0.6:  # >60% veterans
                        passes_filters = False

            # -------------------------------------------------------------------------
            # Add to filtered list if passes all checks
            # -------------------------------------------------------------------------
            if passes_filters:
                filtered.append(proposal)

        return filtered

    def _validate_proposals(
        self,
        proposals: List[TradeProposal],
        team_id: int
    ) -> List[TradeProposal]:
        """
        Validate trade proposals for legal compliance and structural integrity.

        Performs 6 critical validation checks to ensure proposals meet NFL rules,
        cap compliance, roster requirements, and basic trade logic.

        Validation Checks:
        1. Cap Compliance: Both teams have sufficient cap space
        2. Roster Minimums: Both teams maintain legal roster minimums
        3. Trade Deadline: Already enforced in evaluate_daily_transactions
        4. No Duplicate Players: No player appears on both sides
        5. Contract Years Remaining: All assets have active contracts
        6. Fairness Range: Value ratio within acceptable range (0.80-1.20)

        Args:
            proposals: List of trade proposals to validate
            team_id: Team ID for context (1-32)

        Returns:
            List of valid proposals that pass all checks
        """
        if not proposals:
            return []

        valid_proposals = []

        for proposal in proposals:
            # Track validation status
            is_valid = True

            # -------------------------------------------------------------------------
            # Check 1: Cap Compliance (both teams)
            # -------------------------------------------------------------------------
            if not proposal.passes_cap_validation:
                is_valid = False
                # Proposal fails cap validation (already calculated by proposal generator)

            # -------------------------------------------------------------------------
            # Check 2: Roster Minimums (both teams)
            # -------------------------------------------------------------------------
            if not proposal.passes_roster_validation:
                is_valid = False
                # Proposal fails roster validation (already calculated by proposal generator)

            # -------------------------------------------------------------------------
            # Check 3: Trade Deadline Enforcement
            # -------------------------------------------------------------------------
            # Already handled in evaluate_daily_transactions (Week 8 check)
            # No additional check needed here

            # -------------------------------------------------------------------------
            # Check 4: No Duplicate Players
            # -------------------------------------------------------------------------
            # Ensure no player appears on both sides of trade
            team1_player_ids = set()
            team2_player_ids = set()

            for asset in proposal.team1_assets:
                if asset.asset_type == AssetType.PLAYER and asset.player_id:
                    team1_player_ids.add(asset.player_id)

            for asset in proposal.team2_assets:
                if asset.asset_type == AssetType.PLAYER and asset.player_id:
                    team2_player_ids.add(asset.player_id)

            # Check for intersection (duplicate players)
            duplicate_players = team1_player_ids & team2_player_ids
            if duplicate_players:
                is_valid = False
                # Same player cannot be traded by both teams

            # -------------------------------------------------------------------------
            # Check 5: Contract Years Remaining > 0
            # -------------------------------------------------------------------------
            # All traded players must have active contracts
            for asset in proposal.team1_assets + proposal.team2_assets:
                if asset.asset_type == AssetType.PLAYER:
                    if asset.contract_years_remaining is None:
                        is_valid = False
                        # Missing contract data
                        break
                    elif asset.contract_years_remaining <= 0:
                        is_valid = False
                        # Expired contract (cannot trade free agents)
                        break

            # -------------------------------------------------------------------------
            # Check 6: Fairness Within Range (0.80 - 1.20)
            # -------------------------------------------------------------------------
            # Reject trades that are too lopsided (beyond FAIR threshold)
            if proposal.value_ratio < 0.80 or proposal.value_ratio > 1.20:
                is_valid = False
                # Trade is too unfair (SLIGHTLY_UNFAIR or VERY_UNFAIR)

            # -------------------------------------------------------------------------
            # Add to valid list if passes all checks
            # -------------------------------------------------------------------------
            if is_valid:
                valid_proposals.append(proposal)

        return valid_proposals

    def evaluate_trade_offer(
        self,
        team_id: int,
        proposal: TradeProposal,
        current_date: str
    ) -> TradeDecision:
        """
        Evaluate incoming trade offer from another team.

        Integrates with TradeEvaluator from Phase 1.3.2 to determine whether to
        accept, reject, or counter an incoming trade proposal.

        Evaluation Pipeline:
        1. Trade cooldown check - Reject immediately if in 7-day cooldown
        2. Team assessment - Get team needs, cap space, GM archetype
        3. Create TradeEvaluator - Initialize with GM archetype and team context
        4. Evaluate proposal - Delegate to TradeEvaluator.evaluate_proposal()
        5. Return decision - TradeDecision with reasoning and confidence

        Args:
            team_id: Team evaluating the offer (1-32)
            proposal: Incoming trade proposal with all assets
            current_date: Current date (YYYY-MM-DD) for cooldown checking

        Returns:
            TradeDecision with decision type (ACCEPT/REJECT/COUNTER),
            reasoning, confidence, and value analysis

        Raises:
            ValueError: If team_id not in proposal teams
        """
        # Step 1: Validate that team_id is part of this trade
        if team_id not in [proposal.team1_id, proposal.team2_id]:
            raise ValueError(
                f"Team {team_id} cannot evaluate trade between "
                f"teams {proposal.team1_id} and {proposal.team2_id}"
            )

        # Step 2: Check trade cooldown - Auto-reject if in cooldown period
        if self._is_in_trade_cooldown(team_id, current_date):
            # Calculate days since last trade for reasoning
            last_trade_date_str = self._trade_history[team_id]
            last_trade_date = datetime.fromisoformat(last_trade_date_str)
            current_date_obj = datetime.fromisoformat(current_date)
            days_since_trade = (current_date_obj - last_trade_date).days
            days_remaining = self.trade_cooldown_days - days_since_trade

            # Return immediate rejection
            return TradeDecision(
                decision=TradeDecisionType.REJECT,
                reasoning=(
                    f"Team is in trade cooldown period ({days_remaining} days remaining). "
                    f"Last trade executed on {last_trade_date_str}. "
                    f"Will not consider new trades until cooldown expires."
                ),
                confidence=1.0,  # 100% confident in cooldown policy
                original_proposal=proposal,
                counter_offer=None,
                deciding_team_id=team_id,
                deciding_gm_name=None,  # Will be populated by evaluator
                perceived_value_ratio=None,
                objective_value_ratio=proposal.value_ratio
            )

        # Step 3: Assess team situation (needs, cap space, GM archetype, context)
        team_record = {"wins": 0, "losses": 0, "ties": 0}  # Placeholder - would query from standings
        team_needs, cap_space, gm_archetype, team_context = self._assess_team_situation(
            team_id, team_record
        )

        # Step 4: Create TradeEvaluator with GM personality and team context
        evaluator = TradeEvaluator(
            gm_archetype=gm_archetype,
            team_context=team_context,
            trade_value_calculator=self.calculator
        )

        # Step 5: Evaluate proposal from this team's perspective
        decision = evaluator.evaluate_proposal(
            proposal=proposal,
            from_perspective_of=team_id
        )

        # Step 6: Return decision (TradeDecision with all details)
        return decision

    def _record_trade_execution(self, team_id: int, current_date: str) -> None:
        """
        Record trade in history for cooldown tracking.

        Updates internal trade history to track when team last executed a trade.
        Used by _is_in_trade_cooldown() to enforce TRADE_COOLDOWN_DAYS policy.

        This method should be called externally after a trade is ACCEPTED and
        successfully executed (cap validation passed, roster limits satisfied, etc.).

        Args:
            team_id: Team that executed the trade (1-32)
            current_date: Date trade was executed (YYYY-MM-DD)

        Note:
            Future enhancement: Persist to database transaction_history table
            for cross-session cooldown tracking.
        """
        self._trade_history[team_id] = current_date

    # -------------------------------------------------------------------------
    # Performance Metrics
    # -------------------------------------------------------------------------

    def _log_evaluation_metrics(
        self,
        team_id: int,
        evaluation_time_ms: float,
        proposals_generated: int,
        proposals_accepted: int
    ) -> None:
        """
        Log evaluation metrics for monitoring.

        Args:
            team_id: NFL team ID (1-32)
            evaluation_time_ms: Time taken for evaluation (milliseconds)
            proposals_generated: Number of proposals generated
            proposals_accepted: Number of proposals accepted (final output)
        """
        # Print to console for now (database logging in Phase 1.6)
        print(
            f"Team {team_id}: {proposals_generated} proposals generated "
            f"({proposals_accepted} accepted) in {evaluation_time_ms:.2f}ms"
        )

    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Get performance metrics for monitoring.

        Returns:
            Dictionary with evaluation count, proposal count, avg time, success rate
        """
        avg_time = (
            self._total_evaluation_time_ms / self._evaluation_count
            if self._evaluation_count > 0
            else 0.0
        )

        proposals_per_evaluation = (
            self._proposal_count / self._evaluation_count
            if self._evaluation_count > 0
            else 0.0
        )

        # Evaluations that generated at least one proposal
        # Note: We can't track this directly without adding another counter,
        # so we approximate based on proposal count
        evaluation_success_rate = (
            min(self._proposal_count / self._evaluation_count, 1.0)
            if self._evaluation_count > 0
            else 0.0
        )

        return {
            "evaluation_count": self._evaluation_count,
            "proposal_count": self._proposal_count,
            "total_time_ms": self._total_evaluation_time_ms,
            "avg_time_ms": avg_time,
            "proposals_per_evaluation": proposals_per_evaluation,
            "evaluation_success_rate": evaluation_success_rate
        }

    def reset_metrics(self) -> None:
        """Reset performance metrics to zero."""
        self._evaluation_count = 0
        self._proposal_count = 0
        self._total_evaluation_time_ms = 0.0

    def clear_debug_data(self) -> None:
        """
        Clear collected debug data.

        Call this after viewing debug logs to prevent memory buildup
        during long simulations.

        Note: Only has effect if debug_mode=True was set during initialization.
        """
        self._debug_data = []
