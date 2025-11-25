"""
Offseason Handler - Executes offseason phases.

Handles re-signing, free agency, draft, roster cuts, training camp, preseason.
Madden-style simplified offseason flow.
"""

from typing import Any, Dict, List

from ..stage_definitions import Stage, StageType


class OffseasonHandler:
    """
    Handler for offseason stages (Madden-style).

    Each offseason stage has distinct logic:
    - Re-signing: Re-sign your own expiring players
    - Free Agency: Sign available free agents
    - Draft: Run the NFL Draft (7 rounds)
    - Roster Cuts: Cut roster from 90 to 53
    - Training Camp: Finalize depth charts
    - Preseason: Optional exhibition games
    """

    def __init__(self, database_path: str):
        """
        Initialize the handler.

        Args:
            database_path: Path to SQLite database
        """
        self._database_path = database_path

    def execute(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the offseason stage.

        Args:
            stage: The current offseason stage
            context: Execution context with dynasty_id, etc.

        Returns:
            Dictionary with events_processed, transactions, etc.
        """
        # Dispatch to stage-specific handler
        handlers = {
            StageType.OFFSEASON_RESIGNING: self._execute_resigning,
            StageType.OFFSEASON_FREE_AGENCY: self._execute_free_agency,
            StageType.OFFSEASON_DRAFT: self._execute_draft,
            StageType.OFFSEASON_ROSTER_CUTS: self._execute_roster_cuts,
            StageType.OFFSEASON_TRAINING_CAMP: self._execute_training_camp,
            StageType.OFFSEASON_PRESEASON: self._execute_preseason,
        }

        handler = handlers.get(stage.stage_type)
        if handler:
            return handler(stage, context)

        return {
            "games_played": [],
            "events_processed": [],
        }

    def can_advance(self, stage: Stage, context: Dict[str, Any]) -> bool:
        """
        Check if the offseason stage is complete.

        Args:
            stage: The current offseason stage
            context: Execution context

        Returns:
            True if stage is complete
        """
        # TODO: Implement completion checks for each stage
        # For now, return True (allows progression)
        return True

    def requires_interaction(self, stage: Stage) -> bool:
        """
        Check if a stage requires user interaction.

        Args:
            stage: The offseason stage

        Returns:
            True if user interaction needed
        """
        interactive_stages = {
            StageType.OFFSEASON_RESIGNING,    # User decides who to re-sign
            StageType.OFFSEASON_FREE_AGENCY,  # User can sign free agents
            StageType.OFFSEASON_DRAFT,        # User makes draft picks
            StageType.OFFSEASON_ROSTER_CUTS,  # User decides who to cut
        }
        return stage.stage_type in interactive_stages

    def get_stage_preview(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get preview data for the offseason stage (for UI display).

        Args:
            stage: The current offseason stage
            context: Execution context with dynasty_id, user_team_id, etc.

        Returns:
            Dictionary with stage preview data
        """
        stage_type = stage.stage_type
        user_team_id = context.get("user_team_id", 1)

        if stage_type == StageType.OFFSEASON_RESIGNING:
            return {
                "stage_name": "Re-signing Period",
                "description": "Re-sign your team's expiring contract players before they hit free agency.",
                "expiring_players": self._get_expiring_contracts(context, user_team_id),
                "is_interactive": True,
            }
        elif stage_type == StageType.OFFSEASON_FREE_AGENCY:
            return {
                "stage_name": "Free Agency",
                "description": "Sign available free agents from other teams.",
                "free_agents": [],  # Placeholder - future implementation
                "is_interactive": True,
            }
        elif stage_type == StageType.OFFSEASON_DRAFT:
            return {
                "stage_name": "NFL Draft",
                "description": "Select players from the draft class to build your team's future.",
                "draft_picks": [],  # Placeholder - future implementation
                "is_interactive": True,
            }
        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            return {
                "stage_name": "Roster Cuts",
                "description": "Cut your roster from 90 players down to the 53-man limit.",
                "roster_size": 0,  # Placeholder
                "is_interactive": True,
            }
        elif stage_type == StageType.OFFSEASON_TRAINING_CAMP:
            return {
                "stage_name": "Training Camp",
                "description": "Finalize your depth charts and prepare for the season.",
                "is_interactive": False,
            }
        elif stage_type == StageType.OFFSEASON_PRESEASON:
            return {
                "stage_name": "Preseason",
                "description": "Complete preseason preparations and move to the regular season.",
                "is_interactive": False,
            }
        else:
            return {
                "stage_name": stage.display_name,
                "description": "Offseason stage",
                "is_interactive": False,
            }

    def _get_expiring_contracts(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of expiring contracts for a team.

        Args:
            context: Execution context with database APIs
            team_id: Team ID to get expiring contracts for

        Returns:
            List of player dictionaries with contract info
        """
        try:
            from salary_cap.cap_database_api import CapDatabaseAPI
            from database.player_roster_api import PlayerRosterAPI
            from team_management.teams.team_loader import TeamDataLoader

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            cap_api = CapDatabaseAPI(db_path)
            roster_api = PlayerRosterAPI(db_path)
            team_loader = TeamDataLoader()

            # Get all active contracts for this team
            contracts = cap_api.get_team_contracts(
                team_id=team_id,
                dynasty_id=dynasty_id,
                season=season,
                active_only=True
            )

            expiring_players = []

            for contract in contracts:
                player_id = contract.get("player_id")
                years_remaining = contract.get("years_remaining", 0)

                # Contract expires if years_remaining <= 1
                if years_remaining <= 1:
                    # Get player info
                    player_info = roster_api.get_player_by_id(player_id, dynasty_id)

                    if player_info:
                        expiring_players.append({
                            "player_id": player_id,
                            "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                            "position": player_info.get("position", ""),
                            "age": player_info.get("age", 0),
                            "overall": player_info.get("overall_rating", 0),
                            "salary": contract.get("base_salary", 0),
                            "years_remaining": years_remaining,
                            "contract_id": contract.get("contract_id"),
                        })

            # Sort by overall rating (highest first)
            expiring_players.sort(key=lambda x: x.get("overall", 0), reverse=True)

            return expiring_players

        except Exception as e:
            print(f"[OffseasonHandler] Error getting expiring contracts: {e}")
            # Return empty list on error - UI will show "No expiring contracts"
            return []

    def _execute_resigning(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute re-signing phase."""
        events = []

        # TODO: Implement re-signing logic
        # 1. Find all players with expiring contracts on each team
        # 2. AI teams decide who to re-sign
        # 3. User team can choose who to re-sign
        # 4. Players not re-signed become free agents

        events.append("Re-signing period completed")

        return {
            "games_played": [],
            "events_processed": events,
            "resigned": [],  # TODO: List of re-signed players
            "became_free_agents": [],  # TODO: Players entering FA
        }

    def _execute_free_agency(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute free agency phase."""
        events = []

        # TODO: Implement free agency logic
        # 1. Get all available free agents
        # 2. AI teams make signings based on needs
        # 3. User team can sign free agents
        # 4. Process all signings

        events.append("Free Agency completed")

        return {
            "games_played": [],
            "events_processed": events,
            "signings": [],  # TODO: List of signings
        }

    def _execute_draft(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute NFL Draft (7 rounds)."""
        events = []

        # TODO: Implement draft logic
        # 1. Generate/load draft class if needed
        # 2. For each pick (224 total):
        #    - AI teams auto-pick based on needs
        #    - User team makes manual picks (or auto)
        # 3. Assign rookies to teams

        events.append("NFL Draft completed (7 rounds)")

        return {
            "games_played": [],
            "events_processed": events,
            "picks": [],  # TODO: List of draft picks
        }

    def _execute_roster_cuts(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute roster cuts (90 to 53)."""
        events = []

        # TODO: Implement roster cuts
        # 1. For each team with > 53 players
        # 2. AI auto-cuts lowest rated players
        # 3. User can manually select cuts
        # 4. Cut players become free agents

        events.append("Roster cuts completed (90 → 53)")

        return {
            "games_played": [],
            "events_processed": events,
            "cuts": [],  # TODO: List of cut players
        }

    def _execute_training_camp(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute training camp phase."""
        events = []

        # TODO: Implement training camp
        # 1. Auto-generate depth charts based on ratings
        # 2. Optional: Small ratings adjustments
        # 3. Finalize rosters for season

        events.append("Training Camp completed")
        events.append("Depth charts finalized")

        return {
            "games_played": [],
            "events_processed": events,
        }

    def _execute_preseason(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute preseason (optional exhibition games)."""
        events = []

        # TODO: Implement preseason
        # 1. Optional: Simulate 3 exhibition games
        # 2. Or skip entirely and advance to regular season
        # 3. No impact on standings

        events.append("Preseason completed")

        return {
            "games_played": [],  # TODO: Preseason game results
            "events_processed": events,
        }