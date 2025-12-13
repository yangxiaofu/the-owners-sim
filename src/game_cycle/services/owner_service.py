"""
Owner Service - Business logic for Owner Review stage.

Part of Milestone 13: Owner Review.
Coordinates staff hire/fire, directive management, and database persistence.
"""

import random
import uuid
import logging
from typing import Dict, List, Any, Optional

from ..database.owner_directives_api import OwnerDirectivesAPI
from ..database.staff_api import StaffAPI
from .staff_generator_service import StaffGeneratorService


class OwnerService:
    """
    Service for Owner Review stage operations.

    Manages:
    - GM and HC assignments
    - Firing and hiring staff
    - Owner directives (win targets, priorities, wishlists)
    - Persistence to database

    Usage:
        service = OwnerService(db_path, dynasty_id, season)
        current = service.get_current_staff(team_id)
        candidates = service.fire_gm(team_id)
        service.hire_gm(team_id, candidate_id)
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the owner service.

        Args:
            db_path: Path to game_cycle database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded components
        self._directives_api: Optional[OwnerDirectivesAPI] = None
        self._staff_api: Optional[StaffAPI] = None
        self._generator: Optional[StaffGeneratorService] = None

    def _get_directives_api(self) -> OwnerDirectivesAPI:
        """Get or create directives API."""
        if self._directives_api is None:
            self._directives_api = OwnerDirectivesAPI(self._db_path)
        return self._directives_api

    def _get_staff_api(self) -> StaffAPI:
        """Get or create staff API."""
        if self._staff_api is None:
            self._staff_api = StaffAPI(self._db_path)
        return self._staff_api

    def _get_generator(self) -> StaffGeneratorService:
        """Get or create staff generator."""
        if self._generator is None:
            self._generator = StaffGeneratorService()
        return self._generator

    # ==================== Staff Management ====================

    def get_current_staff(self, team_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current GM and HC for a team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with 'gm' and 'hc' keys, or None if no assignment
        """
        return self._get_staff_api().get_staff_assignment(
            self._dynasty_id, team_id, self._season
        )

    def fire_gm(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Fire current GM and generate replacement candidates.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of 3-5 GM candidates

        Raises:
            ValueError: If no current staff exists
        """
        current = self.get_current_staff(team_id)
        exclude = []
        if current:
            exclude = [current["gm"]["archetype_key"]]

        count = random.randint(3, 5)
        candidates = self._get_generator().generate_gm_candidates(
            count=count,
            exclude_archetypes=exclude
        )

        # Save candidates to database
        self._get_staff_api().save_candidates(
            self._dynasty_id, team_id, self._season, "GM", candidates
        )

        self._logger.info(
            f"Generated {len(candidates)} GM candidates for team {team_id}"
        )

        return candidates

    def fire_hc(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Fire current HC and generate replacement candidates.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of 3-5 HC candidates
        """
        current = self.get_current_staff(team_id)
        exclude = []
        if current:
            exclude = [current["hc"]["archetype_key"]]

        count = random.randint(3, 5)
        candidates = self._get_generator().generate_hc_candidates(
            count=count,
            exclude_archetypes=exclude
        )

        # Save candidates to database
        self._get_staff_api().save_candidates(
            self._dynasty_id, team_id, self._season, "HC", candidates
        )

        self._logger.info(
            f"Generated {len(candidates)} HC candidates for team {team_id}"
        )

        return candidates

    def get_gm_candidates(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get saved GM candidates for a team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of candidate dicts
        """
        return self._get_staff_api().get_candidates(
            self._dynasty_id, team_id, self._season, "GM"
        )

    def get_hc_candidates(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get saved HC candidates for a team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of candidate dicts
        """
        return self._get_staff_api().get_candidates(
            self._dynasty_id, team_id, self._season, "HC"
        )

    def hire_gm(self, team_id: int, candidate_id: str) -> Dict[str, Any]:
        """
        Hire a GM from the candidate pool.

        Args:
            team_id: Team ID
            candidate_id: UUID of selected candidate

        Returns:
            Hired GM data

        Raises:
            ValueError: If candidate not found
        """
        candidates = self._get_staff_api().get_candidates(
            self._dynasty_id, team_id, self._season, "GM"
        )

        selected = next(
            (c for c in candidates if c["staff_id"] == candidate_id),
            None
        )

        if not selected:
            raise ValueError(f"GM candidate {candidate_id} not found")

        selected["hire_season"] = self._season

        # Get current HC (or create default)
        current = self.get_current_staff(team_id)
        hc_data = current["hc"] if current else self._create_default_hc()

        # Update assignment
        self._get_staff_api().save_staff_assignment(
            self._dynasty_id, team_id, self._season,
            selected, hc_data
        )

        # Clear GM candidates
        self._get_staff_api().clear_candidates(
            self._dynasty_id, team_id, self._season, "GM"
        )

        self._logger.info(
            f"Hired GM {selected['name']} ({selected['archetype_key']}) for team {team_id}"
        )

        return selected

    def hire_hc(self, team_id: int, candidate_id: str) -> Dict[str, Any]:
        """
        Hire a Head Coach from the candidate pool.

        Args:
            team_id: Team ID
            candidate_id: UUID of selected candidate

        Returns:
            Hired HC data

        Raises:
            ValueError: If candidate not found
        """
        candidates = self._get_staff_api().get_candidates(
            self._dynasty_id, team_id, self._season, "HC"
        )

        selected = next(
            (c for c in candidates if c["staff_id"] == candidate_id),
            None
        )

        if not selected:
            raise ValueError(f"HC candidate {candidate_id} not found")

        selected["hire_season"] = self._season

        # Get current GM (or create default)
        current = self.get_current_staff(team_id)
        gm_data = current["gm"] if current else self._create_default_gm()

        # Update assignment
        self._get_staff_api().save_staff_assignment(
            self._dynasty_id, team_id, self._season,
            gm_data, selected
        )

        # Clear HC candidates
        self._get_staff_api().clear_candidates(
            self._dynasty_id, team_id, self._season, "HC"
        )

        self._logger.info(
            f"Hired HC {selected['name']} ({selected['archetype_key']}) for team {team_id}"
        )

        return selected

    # ==================== Directives Management ====================

    def get_directives(self, team_id: int) -> Optional[Dict[str, Any]]:
        """
        Get owner directives for next season.

        Directives set during Owner Review apply to the upcoming season.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with directive fields, or None if not set
        """
        return self._get_directives_api().get_directives(
            self._dynasty_id, team_id, self._season + 1  # For NEXT season
        )

    def save_directives(self, team_id: int, directives: Dict[str, Any]) -> bool:
        """
        Save owner directives for next season.

        Args:
            team_id: Team ID (1-32)
            directives: Dict with directive fields

        Returns:
            True if successful
        """
        success = self._get_directives_api().save_directives(
            self._dynasty_id, team_id, self._season + 1,  # For NEXT season
            directives
        )

        if success:
            self._logger.info(
                f"Saved directives for team {team_id}, season {self._season + 1}"
            )

        return success

    # ==================== Initialization ====================

    def initialize_default_staff(self, team_id: int) -> Dict[str, Any]:
        """
        Initialize default GM and HC for a new dynasty.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with 'gm' and 'hc' keys
        """
        gm_data = self._create_default_gm()
        hc_data = self._create_default_hc()

        self._get_staff_api().save_staff_assignment(
            self._dynasty_id, team_id, self._season,
            gm_data, hc_data
        )

        self._logger.info(f"Initialized default staff for team {team_id}")

        return {"gm": gm_data, "hc": hc_data}

    def ensure_staff_exists(self, team_id: int) -> Dict[str, Any]:
        """
        Ensure staff assignment exists for a team.

        Checks current season, then tries to copy from previous season,
        then creates defaults if no prior assignment.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with 'gm' and 'hc' keys
        """
        # Try current season
        current = self.get_current_staff(team_id)
        if current:
            return current

        # Try to copy from previous season
        staff_api = self._get_staff_api()
        copied = staff_api.copy_staff_to_next_season(
            self._dynasty_id, team_id, self._season - 1, self._season
        )
        if copied:
            return self.get_current_staff(team_id)

        # Try latest assignment
        latest = staff_api.get_latest_staff_assignment(self._dynasty_id, team_id)
        if latest:
            staff_api.save_staff_assignment(
                self._dynasty_id, team_id, self._season,
                latest["gm"], latest["hc"]
            )
            return {"gm": latest["gm"], "hc": latest["hc"]}

        # Create defaults
        return self.initialize_default_staff(team_id)

    def _create_default_gm(self) -> Dict[str, Any]:
        """Create default GM data for new dynasties."""
        return {
            "staff_id": str(uuid.uuid4()),
            "name": "Default GM",
            "archetype_key": "balanced",
            "custom_traits": {},
            "history": "Experienced front office executive with a balanced approach to roster building.",
            "hire_season": self._season,
        }

    def _create_default_hc(self) -> Dict[str, Any]:
        """Create default HC data for new dynasties."""
        return {
            "staff_id": str(uuid.uuid4()),
            "name": "Default HC",
            "archetype_key": "balanced",
            "custom_traits": {},
            "history": "Veteran coaching background with experience at multiple NFL stops.",
            "hire_season": self._season,
        }

    # ==================== Season Summary ====================

    def get_season_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get season summary for Owner Review display.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with season stats for display
        """
        # Get previous season's target from directives
        prev_directives = self._get_directives_api().get_directives(
            self._dynasty_id, team_id, self._season
        )
        target_wins = prev_directives.get("target_wins") if prev_directives else None

        # Note: Actual wins/losses should be fetched from standings
        # This is a placeholder - integrate with StandingsAPI
        return {
            "season": self._season,
            "target_wins": target_wins,
            "wins": None,  # TODO: Get from standings
            "losses": None,  # TODO: Get from standings
        }
