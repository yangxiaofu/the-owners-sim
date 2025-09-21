"""
User Team Manager

Provides a clean interface for managing which team the user controls in their dynasty.
Integrates with existing DynastyContext and TeamDataLoader components.
"""

from typing import Optional
import logging

# Dynasty context removed with calendar system
# from simulation.dynasty_context import DynastyContext, get_dynasty_context
from team_management.teams.team_loader import TeamDataLoader, Team


class UserTeamManager:
    """
    Manages the user's team selection and provides easy access to user team information.

    This class acts as a bridge between the dynasty context and team data systems,
    providing a clean interface for user team operations while leveraging existing
    infrastructure.
    """

    def __init__(self, dynasty_context: Optional[DynastyContext] = None):
        """
        Initialize UserTeamManager.

        Args:
            dynasty_context: Dynasty context instance. If None, uses global instance.
        """
        self.dynasty_context = dynasty_context or get_dynasty_context()
        self.team_loader = TeamDataLoader()
        self.logger = logging.getLogger(__name__)

        # Metadata key for storing user team ID
        self._USER_TEAM_KEY = 'user_team_id'

    def set_user_team(self, team_id: int) -> None:
        """
        Set which team the user controls.

        Args:
            team_id: Numerical team ID (1-32)

        Raises:
            ValueError: If team_id is not valid (must be 1-32)
            RuntimeError: If dynasty is not initialized
        """
        if not self.dynasty_context.is_initialized():
            raise RuntimeError("Dynasty must be initialized before setting user team")

        if not self._is_valid_team_id(team_id):
            raise ValueError(f"Invalid team ID: {team_id}. Must be between 1 and 32.")

        # Verify team exists in our data
        team = self.team_loader.get_team_by_id(team_id)
        if not team:
            raise ValueError(f"Team with ID {team_id} not found in team data")

        self.dynasty_context.set_metadata(self._USER_TEAM_KEY, team_id)
        self.logger.info(f"User team set to {team.full_name} (ID: {team_id})")

    def get_user_team_id(self) -> Optional[int]:
        """
        Get the user's team ID.

        Returns:
            Team ID if set, None otherwise
        """
        return self.dynasty_context.get_metadata(self._USER_TEAM_KEY)

    def get_user_team(self) -> Optional[Team]:
        """
        Get the full Team object for the user's team.

        Returns:
            Team object if user team is set, None otherwise
        """
        team_id = self.get_user_team_id()
        if team_id is None:
            return None

        return self.team_loader.get_team_by_id(team_id)

    def is_user_team(self, team_id: int) -> bool:
        """
        Check if the given team ID is the user's team.

        Args:
            team_id: Team ID to check

        Returns:
            True if this is the user's team, False otherwise
        """
        user_team_id = self.get_user_team_id()
        return user_team_id is not None and user_team_id == team_id

    def clear_user_team(self) -> None:
        """
        Clear the user's team selection.
        """
        self.dynasty_context.set_metadata(self._USER_TEAM_KEY, None)
        self.logger.info("User team selection cleared")

    def has_user_team(self) -> bool:
        """
        Check if the user has selected a team.

        Returns:
            True if user has selected a team, False otherwise
        """
        return self.get_user_team_id() is not None

    def get_user_team_name(self) -> Optional[str]:
        """
        Get the full name of the user's team.

        Returns:
            Team full name if set, None otherwise
        """
        team = self.get_user_team()
        return team.full_name if team else None

    def get_user_team_abbreviation(self) -> Optional[str]:
        """
        Get the abbreviation of the user's team.

        Returns:
            Team abbreviation if set, None otherwise
        """
        team = self.get_user_team()
        return team.abbreviation if team else None

    def get_division_rivals(self) -> list[Team]:
        """
        Get the user's division rivals.

        Returns:
            List of Team objects in the same division (excluding user's team)
        """
        user_team_id = self.get_user_team_id()
        if user_team_id is None:
            return []

        return self.team_loader.get_division_rivals(user_team_id)

    def _is_valid_team_id(self, team_id: int) -> bool:
        """
        Validate team ID range.

        Args:
            team_id: Team ID to validate

        Returns:
            True if valid (1-32), False otherwise
        """
        return isinstance(team_id, int) and 1 <= team_id <= 32

    def get_summary(self) -> dict:
        """
        Get a summary of the user's team information.

        Returns:
            Dictionary with user team information
        """
        team = self.get_user_team()

        if not team:
            return {
                'has_team': False,
                'team_id': None,
                'team_name': None,
                'abbreviation': None,
                'conference': None,
                'division': None
            }

        return {
            'has_team': True,
            'team_id': team.team_id,
            'team_name': team.full_name,
            'abbreviation': team.abbreviation,
            'conference': team.conference,
            'division': team.division,
            'city': team.city,
            'nickname': team.nickname
        }

    def __str__(self) -> str:
        """String representation."""
        team_name = self.get_user_team_name()
        if team_name:
            return f"UserTeamManager: {team_name}"
        return "UserTeamManager: No team selected"

    def __repr__(self) -> str:
        """Detailed representation."""
        team_id = self.get_user_team_id()
        team_name = self.get_user_team_name()
        return f"UserTeamManager(team_id={team_id}, team_name='{team_name}')"