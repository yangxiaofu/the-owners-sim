"""
Draft Dialog Controller

Business logic controller for interactive NFL draft day dialog.
Orchestrates draft operations between UI and backend systems.

Architecture:
- Thin controller pattern (≤10-20 lines per method)
- Delegates business logic to DraftManager
- Persists state via DynastyStateAPI
- Ensures dynasty isolation throughout

Responsibilities:
- Draft order and prospect retrieval
- User pick execution validation
- AI pick simulation orchestration
- Draft progress persistence
- State recovery for resume capability

Usage Example:
    >>> from ui.controllers.draft_dialog_controller import DraftDialogController
    >>> controller = DraftDialogController(
    ...     database_path="data/database/nfl_simulation.db",
    ...     dynasty_id="my_dynasty",
    ...     season_year=2025,
    ...     user_team_id=22
    ... )
    >>> # Connect to signals
    >>> controller.pick_executed.connect(on_pick_executed)
    >>> # Execute pick
    >>> result = controller.execute_user_pick(player_id=1001)
"""

from typing import Optional, List, Dict, Any
import logging
from PySide6.QtCore import QObject, Signal

# Database APIs
from src.database.draft_class_api import DraftClassAPI
from src.database.draft_order_database_api import DraftOrderDatabaseAPI, DraftPick
from src.database.dynasty_state_api import DynastyStateAPI

# Business logic
from src.offseason.draft_manager import DraftManager
from src.offseason.team_needs_analyzer import TeamNeedsAnalyzer

# Utilities
from src.team_management.teams.team_loader import TeamDataLoader


class DraftDialogController(QObject):
    """
    Controller for draft day dialog business logic.

    Manages draft flow, prospect evaluation, and pick execution for both
    user-controlled and AI-controlled teams. Integrates with dynasty state
    for resumable draft sessions.

    Features:
    - Draft order tracking (1-262 picks, 7 rounds)
    - Available prospect retrieval with filtering
    - Team needs analysis integration
    - User pick execution with validation
    - AI pick simulation with needs-based evaluation
    - Pick history tracking
    - Save/resume draft state

    Signals:
        pick_executed: Emitted after successful pick (pick_number, player_id, team_id)
        draft_completed: Emitted when all 262 picks executed
        error_occurred: Emitted on operation failure (error_message)
    """

    # Qt signals for UI updates
    pick_executed = Signal(int, int, int)  # (pick_number, player_id, team_id)
    draft_completed = Signal()
    error_occurred = Signal(str)  # (error_message)

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        user_team_id: int
    ):
        """
        Initialize draft dialog controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for isolation
            season_year: Draft season year (e.g., 2025)
            user_team_id: User's team ID (1-32)

        Raises:
            ValueError: If draft order or draft class not found
        """
        super().__init__()

        # Store parameters
        self.db_path = database_path
        self.dynasty_id = dynasty_id
        self._season = season_year
        self._user_team_id = user_team_id

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize database APIs
        self.draft_api = DraftClassAPI(database_path)
        self.draft_order_api = DraftOrderDatabaseAPI(database_path)
        self.dynasty_state_api = DynastyStateAPI(database_path)
        self.needs_analyzer = TeamNeedsAnalyzer(database_path, dynasty_id)
        self.team_loader = TeamDataLoader()

        # Initialize DraftManager (business logic)
        self.draft_manager = DraftManager(
            database_path=database_path,
            dynasty_id=dynasty_id,
            season_year=season_year,
            enable_persistence=True
        )

        # Load draft order from database
        self._draft_order = self._load_draft_order()

        # Load saved draft state (resume support)
        state = self.load_draft_state()
        self.current_pick_index = state['current_pick_index']

        # Validate draft class exists
        if not self.draft_api.dynasty_has_draft_class(dynasty_id, season_year):
            raise ValueError(
                f"No draft class found for dynasty '{dynasty_id}', season {season_year}. "
                f"Generate draft class before starting draft."
            )

        self.logger.info(
            f"Initialized DraftDialogController: dynasty={dynasty_id}, "
            f"season={season_year}, user_team={user_team_id}, "
            f"current_pick={self.current_pick_index}"
        )

    # Properties for dialog compatibility
    @property
    def user_team_id(self) -> int:
        """User's team ID (1-32)."""
        return self._user_team_id

    @property
    def season(self) -> int:
        """Current draft season year."""
        return self._season

    @property
    def draft_order(self) -> List[DraftPick]:
        """Complete draft order (all 262 picks)."""
        return self._draft_order

    def _load_draft_order(self) -> List[DraftPick]:
        """
        Load complete draft order from database.

        Returns:
            List of DraftPick objects ordered by overall_pick

        Raises:
            ValueError: If draft order not found
        """
        draft_order = self.draft_order_api.get_draft_order(
            dynasty_id=self.dynasty_id,
            season=self._season
        )

        if not draft_order:
            raise ValueError(
                f"No draft order found for dynasty '{self.dynasty_id}', "
                f"season {self._season}. Generate draft order before starting draft."
            )

        self.logger.info(f"Loaded {len(draft_order)} draft picks")
        return draft_order

    def load_draft_data(self) -> Dict[str, Any]:
        """
        Load draft order and draft class from database.

        Retrieves complete draft order (262 picks) and available prospects,
        then determines current pick position from dynasty state.

        Returns:
            Dict containing:
            {
                'draft_order': List[DraftPick],
                'total_picks': int,
                'current_pick_index': int,
                'prospects_available': int
            }

        Raises:
            ValueError: If draft order or draft class not found
        """
        # Get draft order (already loaded in __init__)
        draft_order = self._draft_order

        # Get available prospects count
        prospects = self.draft_api.get_all_prospects(
            dynasty_id=self.dynasty_id,
            season=self._season,
            available_only=True
        )

        # Load current pick state
        state = self.load_draft_state()

        self.logger.info(
            f"Loaded draft data: {len(draft_order)} picks, "
            f"{len(prospects)} prospects available"
        )

        return {
            'draft_order': draft_order,
            'total_picks': len(draft_order),
            'current_pick_index': state['current_pick_index'],
            'prospects_available': len(prospects)
        }

    def get_current_pick(self) -> Optional[Dict[str, Any]]:
        """
        Get current pick information.

        Returns:
            Dict with pick details, or None if draft is complete:
            {
                'round': int,
                'pick_in_round': int,
                'overall_pick': int,
                'team_id': int,
                'team_name': str,
                'is_user_pick': bool,
                'pick_id': int
            }
        """
        # Check if draft complete
        if self.current_pick_index >= len(self._draft_order):
            return None

        # Get current pick object
        pick = self._draft_order[self.current_pick_index]

        # Get team name
        team = self.team_loader.get_team_by_id(pick.current_team_id)
        team_name = team.full_name if team else f"Team {pick.current_team_id}"

        return {
            'round': pick.round_number,
            'pick_in_round': pick.pick_in_round,
            'overall_pick': pick.overall_pick,
            'team_id': pick.current_team_id,
            'team_name': team_name,
            'is_user_pick': pick.current_team_id == self._user_team_id,
            'pick_id': pick.pick_id
        }

    def get_available_prospects(
        self,
        limit: int = 100,
        position_filter: Optional[str] = None,
        sort_by: str = "overall"
    ) -> List[Dict[str, Any]]:
        """
        Get available (undrafted) prospects with optional filtering.

        Args:
            limit: Maximum prospects to return (default 100)
            position_filter: Optional position filter (e.g., "QB", "WR")
            sort_by: Sort field ("overall", "projected_pick_min", "position")

        Returns:
            List of prospect dicts sorted by specified field:
            [
                {
                    'player_id': int,
                    'first_name': str,
                    'last_name': str,
                    'position': str,
                    'overall': int,
                    'college': str,
                    'age': int,
                    'projected_pick_min': int,
                    'projected_pick_max': int,
                    ...
                },
                ...
            ]
        """
        # Delegate to DraftClassAPI
        prospects = self.draft_api.get_all_prospects(
            dynasty_id=self.dynasty_id,
            season=self._season,
            available_only=True
        )

        # Apply position filter if specified
        if position_filter:
            prospects = [p for p in prospects if p['position'] == position_filter]

        # Sort by specified field (descending for overall/ratings)
        reverse = sort_by in ["overall", "projected_pick_min"]
        prospects.sort(key=lambda p: p.get(sort_by, 0), reverse=reverse)

        # Return top N
        return prospects[:limit]

    def get_team_needs(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get team needs sorted by urgency.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of need dicts sorted by urgency (CRITICAL → LOW):
            [
                {
                    'position': str,
                    'urgency': NeedUrgency,
                    'urgency_score': int,
                    'starter_overall': int,
                    'depth_count': int,
                    'avg_depth_overall': float,
                    'reason': str
                },
                ...
            ]
        """
        # Delegate to TeamNeedsAnalyzer
        needs = self.needs_analyzer.analyze_team_needs(
            team_id=team_id,
            season=self._season,
            include_future_contracts=True
        )

        return needs  # Already sorted by urgency (CRITICAL → LOW)

    def execute_user_pick(self, player_id: int) -> Dict[str, Any]:
        """
        Execute user's draft pick.

        Validates pick ownership, executes via DraftManager, updates database,
        advances to next pick, and emits signals.

        Args:
            player_id: Player ID of prospect to draft

        Returns:
            Dict with pick result:
            {
                'success': bool,
                'player_id': int,
                'player_name': str,
                'position': str,
                'overall': int,
                'round': int,
                'pick': int,
                'overall_pick': int,
                'team_id': int,
                'team_name': str,
                'college': str,
                'message': str  # (if success=False)
            }

        Raises:
            ValueError: If not user's pick or player not available
        """
        # Get current pick
        current_pick = self.get_current_pick()
        if not current_pick:
            raise ValueError("Draft is complete, no picks remaining")

        # Validate it's user's pick
        if not current_pick['is_user_pick']:
            raise ValueError(
                f"Not user's pick. Current pick belongs to {current_pick['team_name']}"
            )

        # Verify player is available
        prospect = self.draft_api.get_prospect_by_id(player_id, self.dynasty_id)
        if not prospect:
            raise ValueError(f"Prospect {player_id} not found")
        if prospect['is_drafted']:
            raise ValueError(f"Prospect {player_id} already drafted")

        # Execute pick via DraftManager
        pick_obj = self._draft_order[self.current_pick_index]
        result = self.draft_manager.make_draft_selection(
            round_num=pick_obj.round_number,
            pick_num=pick_obj.pick_in_round,
            player_id=player_id,
            team_id=pick_obj.current_team_id
        )

        # Update draft order state
        self.draft_order_api.mark_pick_executed(pick_obj.pick_id, player_id)
        self._draft_order[self.current_pick_index].is_executed = True
        self._draft_order[self.current_pick_index].player_id = player_id

        # Advance to next pick
        self.current_pick_index += 1

        # Save state to database
        self.save_draft_state()

        # Emit signal
        self.pick_executed.emit(pick_obj.overall_pick, player_id, pick_obj.current_team_id)

        # Check if draft complete
        if self.is_draft_complete():
            self.draft_completed.emit()

        # Get team name
        team = self.team_loader.get_team_by_id(pick_obj.current_team_id)
        team_name = team.full_name if team else f"Team {pick_obj.current_team_id}"

        self.logger.info(
            f"User executed pick {pick_obj.overall_pick}: "
            f"{prospect['first_name']} {prospect['last_name']} "
            f"({prospect['position']}, {prospect['overall']} OVR)"
        )

        return {
            'success': True,
            'player_id': player_id,
            'player_name': f"{prospect['first_name']} {prospect['last_name']}",
            'position': prospect['position'],
            'overall': prospect['overall'],
            'round': pick_obj.round_number,
            'pick': pick_obj.pick_in_round,
            'overall_pick': pick_obj.overall_pick,
            'team_id': pick_obj.current_team_id,
            'team_name': team_name,
            'college': prospect.get('college', 'Unknown')
        }

    def execute_ai_pick(self) -> Dict[str, Any]:
        """
        Execute AI team's draft pick using needs-based evaluation.

        Uses DraftManager's prospect evaluation to score all available
        prospects based on team needs and selects highest-scoring player.

        Returns:
            Dict with pick result:
            {
                'success': bool,
                'player_id': int,
                'player_name': str,
                'position': str,
                'overall': int,
                'round': int,
                'pick': int,
                'overall_pick': int,
                'team_id': int,
                'team_name': str,
                'college': str,
                'needs_match': str,
                'eval_score': float
            }

        Raises:
            ValueError: If current pick belongs to user or no prospects available
        """
        # Get current pick
        current_pick = self.get_current_pick()
        if not current_pick:
            raise ValueError("Draft is complete, no picks remaining")

        # Validate it's AI's pick
        if current_pick['is_user_pick']:
            raise ValueError("Current pick belongs to user, not AI")

        pick_obj = self._draft_order[self.current_pick_index]
        team_id = pick_obj.current_team_id

        # Get available prospects and team needs
        available_prospects = self.get_available_prospects(limit=500)
        if not available_prospects:
            raise ValueError("No prospects available to draft")

        team_needs = self.get_team_needs(team_id)

        # Evaluate prospects using DraftManager's AI
        best_prospect = None
        best_score = -1

        for prospect in available_prospects:
            score = self.draft_manager._evaluate_prospect(
                prospect=prospect,
                team_needs=team_needs,
                pick_position=pick_obj.overall_pick
            )
            if score > best_score:
                best_score = score
                best_prospect = prospect

        if not best_prospect:
            raise ValueError("No suitable prospect found for AI team")

        player_id = best_prospect['player_id']

        # Execute pick via DraftManager
        result = self.draft_manager.make_draft_selection(
            round_num=pick_obj.round_number,
            pick_num=pick_obj.pick_in_round,
            player_id=player_id,
            team_id=team_id
        )

        # Update draft order state
        self.draft_order_api.mark_pick_executed(pick_obj.pick_id, player_id)
        self._draft_order[self.current_pick_index].is_executed = True
        self._draft_order[self.current_pick_index].player_id = player_id

        # Advance to next pick
        self.current_pick_index += 1

        # Save state
        self.save_draft_state()

        # Emit signal
        self.pick_executed.emit(pick_obj.overall_pick, player_id, team_id)

        # Check completion
        if self.is_draft_complete():
            self.draft_completed.emit()

        # Get team name
        team = self.team_loader.get_team_by_id(team_id)
        team_name = team.full_name if team else f"Team {team_id}"

        # Determine needs match
        needs_match = "NONE"
        for need in team_needs:
            if need['position'] == best_prospect['position']:
                needs_match = need['urgency'].name
                break

        self.logger.info(
            f"AI executed pick {pick_obj.overall_pick}: "
            f"Team {team_id} selects {best_prospect['first_name']} {best_prospect['last_name']} "
            f"({best_prospect['position']}, {best_prospect['overall']} OVR) "
            f"[Need: {needs_match}, Score: {best_score:.1f}]"
        )

        return {
            'success': True,
            'player_id': player_id,
            'player_name': f"{best_prospect['first_name']} {best_prospect['last_name']}",
            'position': best_prospect['position'],
            'overall': best_prospect['overall'],
            'round': pick_obj.round_number,
            'pick': pick_obj.pick_in_round,
            'overall_pick': pick_obj.overall_pick,
            'team_id': team_id,
            'team_name': team_name,
            'college': best_prospect.get('college', 'Unknown'),
            'needs_match': needs_match,
            'eval_score': round(best_score, 1)
        }

    def get_pick_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Get recent draft picks (most recent first).

        Args:
            limit: Maximum number of picks to return (default 15)

        Returns:
            List of executed pick dicts (most recent first):
            [
                {
                    'round': int,
                    'pick': int,
                    'overall_pick': int,
                    'team_id': int,
                    'team_name': str,
                    'player_id': int,
                    'player_name': str,
                    'position': str,
                    'overall': int,
                    'college': str
                },
                ...
            ]
        """
        executed_picks = []

        # Iterate backwards from current pick (most recent first)
        for idx in range(self.current_pick_index - 1, -1, -1):
            if len(executed_picks) >= limit:
                break

            pick = self._draft_order[idx]

            if not pick.is_executed or not pick.player_id:
                continue

            # Get prospect info
            prospect = self.draft_api.get_prospect_by_id(pick.player_id, self.dynasty_id)
            if not prospect:
                continue

            # Get team name
            team = self.team_loader.get_team_by_id(pick.current_team_id)
            team_name = team.full_name if team else f"Team {pick.current_team_id}"

            executed_picks.append({
                'round': pick.round_number,
                'pick': pick.pick_in_round,
                'overall_pick': pick.overall_pick,
                'team_id': pick.current_team_id,
                'team_name': team_name,
                'player_id': pick.player_id,
                'player_name': f"{prospect['first_name']} {prospect['last_name']}",
                'position': prospect['position'],
                'overall': prospect['overall'],
                'college': prospect.get('college', 'Unknown')
            })

        return executed_picks

    def is_draft_complete(self) -> bool:
        """
        Check if draft is complete.

        Returns:
            True if all 262 picks have been executed
        """
        return self.current_pick_index >= len(self._draft_order)

    def get_draft_progress(self) -> Dict[str, Any]:
        """
        Get overall draft progress.

        Returns:
            Dict with draft progress info:
            {
                'picks_completed': int,
                'picks_remaining': int,
                'total_picks': int,
                'completion_pct': float,
                'current_round': int,
                'is_complete': bool
            }
        """
        total_picks = len(self._draft_order)
        picks_completed = self.current_pick_index
        picks_remaining = total_picks - picks_completed

        current_pick = self.get_current_pick()
        current_round = current_pick['round'] if current_pick else 7

        completion_pct = (picks_completed / total_picks * 100) if total_picks > 0 else 0

        return {
            'picks_completed': picks_completed,
            'picks_remaining': picks_remaining,
            'total_picks': total_picks,
            'completion_pct': round(completion_pct, 1),
            'current_round': current_round,
            'is_complete': self.is_draft_complete()
        }

    def save_draft_state(self) -> bool:
        """
        Save current draft state to database.

        Persists current pick index and draft-in-progress flag to dynasty_state
        table for resume capability.

        Returns:
            True if save successful, False otherwise

        Raises:
            RuntimeError: If database write fails (fail-loud)
        """
        try:
            # Delegate to DynastyStateAPI.update_draft_progress()
            success = self.dynasty_state_api.update_draft_progress(
                dynasty_id=self.dynasty_id,
                season=self._season,
                current_pick=self.current_pick_index,
                in_progress=not self.is_draft_complete()
            )

            if not success:
                raise RuntimeError("update_draft_progress() returned False")

            self.logger.debug(
                f"Draft state saved: pick={self.current_pick_index}, "
                f"complete={self.is_draft_complete()}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to save draft state: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to save draft state: {str(e)}")
            raise RuntimeError(f"Draft state persistence failed: {e}")

    def load_draft_state(self) -> Dict[str, Any]:
        """
        Load saved draft state from database.

        Retrieves current pick index and draft status from dynasty_state table.
        Returns default values if no saved state exists (new draft).

        Returns:
            Dict with saved state:
            {
                'current_pick_index': int,
                'draft_in_progress': bool,
                'last_saved': str  # ISO timestamp
            }
        """
        try:
            # Get latest dynasty state (includes draft progress fields)
            state = self.dynasty_state_api.get_latest_state(self.dynasty_id)

            if not state:
                # No state exists - return defaults for new draft
                return {
                    'current_pick_index': 0,
                    'draft_in_progress': False,
                    'last_saved': ''
                }

            return {
                'current_pick_index': state.get('current_draft_pick', 0),
                'draft_in_progress': state.get('draft_in_progress', False),
                'last_saved': ''  # TODO: Add updated_at if needed
            }

        except Exception as e:
            self.logger.warning(f"Failed to load draft state: {e}")
            # Return defaults for new draft
            return {
                'current_pick_index': 0,
                'draft_in_progress': False,
                'last_saved': ''
            }
