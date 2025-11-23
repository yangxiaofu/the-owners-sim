"""
Draft Demo Controller

Business logic controller for interactive draft day simulation.

Responsibilities:
- Draft order management and tracking
- Prospect retrieval and filtering
- User pick execution
- AI pick simulation with team needs evaluation
- Pick history tracking
"""

from typing import Optional, List, Dict, Any
import logging

from database.draft_class_api import DraftClassAPI
from database.draft_order_database_api import DraftOrderDatabaseAPI, DraftPick
from offseason.draft_manager import DraftManager
from offseason.team_needs_analyzer import TeamNeedsAnalyzer
from team_management.teams.team_loader import TeamDataLoader


class DraftDemoController:
    """
    Controller for draft day simulation business logic.

    Manages draft flow, prospect evaluation, and pick execution for both
    user-controlled and AI-controlled teams.

    Features:
    - Draft order tracking (1-224 picks)
    - Available prospect retrieval
    - Team needs analysis
    - User pick execution
    - AI pick simulation with needs-based evaluation
    - Pick history tracking
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        user_team_id: int
    ):
        """
        Initialize draft demo controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier
            season: Draft season year (e.g., 2025)
            user_team_id: User's team ID (1-32)

        Raises:
            ValueError: If draft order or draft class not found
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season
        self.user_team_id = user_team_id

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize APIs and managers
        self.draft_api = DraftClassAPI(db_path)
        self.draft_order_api = DraftOrderDatabaseAPI(db_path)
        self.draft_manager = DraftManager(
            database_path=db_path,
            dynasty_id=dynasty_id,
            season_year=season,
            enable_persistence=True
        )
        self.needs_analyzer = TeamNeedsAnalyzer(db_path, dynasty_id)
        self.team_loader = TeamDataLoader()

        # Load draft order
        self.draft_order = self._load_draft_order()

        # Track current pick index (0-223 for 224 picks)
        self.current_pick_index = self._find_current_pick_index()

        # Validate draft class exists
        if not self.draft_api.dynasty_has_draft_class(dynasty_id, season):
            raise ValueError(
                f"No draft class found for dynasty '{dynasty_id}', season {season}. "
                f"Generate draft class before starting draft."
            )

        self.logger.info(
            f"Initialized DraftDemoController for dynasty '{dynasty_id}', "
            f"season {season}, user team {user_team_id}"
        )

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
            season=self.season
        )

        if not draft_order:
            raise ValueError(
                f"No draft order found for dynasty '{self.dynasty_id}', season {self.season}. "
                f"Generate draft order before starting draft."
            )

        self.logger.info(f"Loaded {len(draft_order)} draft picks")
        return draft_order

    def _find_current_pick_index(self) -> int:
        """
        Find index of current pick (first unexecuted pick).

        Returns:
            Index of current pick (0-223), or len(draft_order) if draft complete
        """
        for idx, pick in enumerate(self.draft_order):
            if not pick.is_executed:
                return idx

        # Draft complete
        return len(self.draft_order)

    def get_current_pick(self) -> Optional[Dict[str, Any]]:
        """
        Get current pick information.

        Returns:
            Dict with pick details, or None if draft is complete:
            {
                'round': 1,
                'pick_in_round': 5,
                'overall_pick': 5,
                'team_id': 22,
                'team_name': 'Detroit Lions',
                'is_user_pick': True
            }
        """
        if self.current_pick_index >= len(self.draft_order):
            # Draft complete
            return None

        pick = self.draft_order[self.current_pick_index]

        # Get team name
        team = self.team_loader.get_team_by_id(pick.current_team_id)
        team_name = team.full_name if team else f"Team {pick.current_team_id}"

        return {
            'round': pick.round_number,
            'pick_in_round': pick.pick_in_round,
            'overall_pick': pick.overall_pick,
            'team_id': pick.current_team_id,
            'team_name': team_name,
            'is_user_pick': pick.current_team_id == self.user_team_id,
            'pick_id': pick.pick_id
        }

    def get_available_prospects(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get available (undrafted) prospects sorted by overall rating.

        Args:
            limit: Maximum number of prospects to return (default 100)

        Returns:
            List of prospect dicts sorted by overall rating (descending):
            [
                {
                    'player_id': 12345,
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'position': 'QB',
                    'overall': 85,
                    'college': 'Ohio State',
                    'age': 21,
                    'projected_pick_min': 8,
                    'projected_pick_max': 15,
                    ...
                },
                ...
            ]
        """
        prospects = self.draft_api.get_all_prospects(
            dynasty_id=self.dynasty_id,
            season=self.season,
            available_only=True
        )

        # Sort by overall rating (descending)
        prospects.sort(key=lambda p: p['overall'], reverse=True)

        # Return top N prospects
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
                    'position': 'quarterback',
                    'urgency': <NeedUrgency.CRITICAL>,
                    'urgency_score': 5,
                    'starter_overall': 65,
                    'depth_count': 1,
                    'avg_depth_overall': 60.0,
                    'starter_leaving': False,
                    'reason': 'No quality starter (65 overall)'
                },
                ...
            ]
        """
        needs = self.needs_analyzer.analyze_team_needs(
            team_id=team_id,
            season=self.season,
            include_future_contracts=True
        )

        return needs

    def execute_user_pick(self, player_id: int) -> Dict[str, Any]:
        """
        Execute user's draft pick.

        Args:
            player_id: Player ID of prospect to draft

        Returns:
            Dict with pick details:
            {
                'success': True,
                'player_id': 12345,
                'player_name': 'John Doe',
                'position': 'QB',
                'overall': 85,
                'round': 1,
                'pick': 5,
                'overall_pick': 5,
                'team_id': 22,
                'team_name': 'Detroit Lions'
            }

        Raises:
            ValueError: If not user's pick or player not available
        """
        current_pick = self.get_current_pick()

        if not current_pick:
            raise ValueError("Draft is complete, no picks remaining")

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

        # Execute pick using DraftManager
        pick_obj = self.draft_order[self.current_pick_index]

        result = self.draft_manager.make_draft_selection(
            round_num=pick_obj.round_number,
            pick_num=pick_obj.pick_in_round,
            player_id=player_id,
            team_id=pick_obj.current_team_id
        )

        # Mark pick as executed in draft order
        self.draft_order_api.mark_pick_executed(
            pick_id=pick_obj.pick_id,
            player_id=player_id
        )

        # Update local draft order state
        self.draft_order[self.current_pick_index].is_executed = True
        self.draft_order[self.current_pick_index].player_id = player_id

        # Advance to next pick
        self.current_pick_index += 1

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

        Uses DraftManager's _evaluate_prospect method to score all available
        prospects based on team needs and selects the highest-scoring player.

        Returns:
            Dict with pick details:
            {
                'success': True,
                'player_id': 12345,
                'player_name': 'John Doe',
                'position': 'QB',
                'overall': 85,
                'round': 1,
                'pick': 5,
                'overall_pick': 5,
                'team_id': 9,
                'team_name': 'Houston Texans',
                'needs_match': 'CRITICAL'
            }

        Raises:
            ValueError: If not AI's pick or no prospects available
        """
        current_pick = self.get_current_pick()

        if not current_pick:
            raise ValueError("Draft is complete, no picks remaining")

        if current_pick['is_user_pick']:
            raise ValueError("Current pick belongs to user, not AI")

        pick_obj = self.draft_order[self.current_pick_index]
        team_id = pick_obj.current_team_id

        # Get available prospects
        available_prospects = self.get_available_prospects(limit=500)

        if not available_prospects:
            raise ValueError("No prospects available to draft")

        # Get team needs
        team_needs = self.get_team_needs(team_id)

        # Evaluate all prospects using DraftManager's evaluation logic
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

        # Execute pick using DraftManager
        result = self.draft_manager.make_draft_selection(
            round_num=pick_obj.round_number,
            pick_num=pick_obj.pick_in_round,
            player_id=player_id,
            team_id=team_id
        )

        # Mark pick as executed in draft order
        self.draft_order_api.mark_pick_executed(
            pick_id=pick_obj.pick_id,
            player_id=player_id
        )

        # Update local draft order state
        self.draft_order[self.current_pick_index].is_executed = True
        self.draft_order[self.current_pick_index].player_id = player_id

        # Advance to next pick
        self.current_pick_index += 1

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
                    'round': 1,
                    'pick': 5,
                    'overall_pick': 5,
                    'team_id': 22,
                    'team_name': 'Detroit Lions',
                    'player_id': 12345,
                    'player_name': 'John Doe',
                    'position': 'QB',
                    'overall': 85,
                    'college': 'Ohio State'
                },
                ...
            ]
        """
        # Get executed picks (reverse order for most recent first)
        executed_picks = []

        for idx in range(self.current_pick_index - 1, -1, -1):
            if len(executed_picks) >= limit:
                break

            pick = self.draft_order[idx]

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
            True if all picks have been executed
        """
        return self.current_pick_index >= len(self.draft_order)

    def get_draft_progress(self) -> Dict[str, Any]:
        """
        Get overall draft progress.

        Returns:
            Dict with draft progress info:
            {
                'picks_completed': 32,
                'picks_remaining': 192,
                'total_picks': 224,
                'completion_pct': 14.3,
                'current_round': 2,
                'is_complete': False
            }
        """
        total_picks = len(self.draft_order)
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
