"""
DirectiveLoader - Centralized owner directive loading with consistent error handling.

Eliminates 7+ duplicate directive loading blocks across offseason.py.
Fixes constructor inconsistencies and provides unified season offset logic.
"""

from typing import Optional
import traceback

from ..models.owner_directives import OwnerDirectives
from ..models.draft_direction import DraftDirection
from ..models.fa_guidance import FAGuidance
from ..database.owner_directives_api import OwnerDirectivesAPI
from ..database.connection import GameCycleDatabase


class DirectiveLoader:
    """
    Centralized loader for owner directives across offseason stages.

    Provides:
    - Consistent error handling
    - Unified season offset logic (season+1 for offseason stages)
    - Conversion to stage-specific models (DraftDirection, FAGuidance)
    - Fixes constructor bugs from offseason.py
    """

    def __init__(self, db_path: str):
        """
        Initialize the directive loader.

        Args:
            db_path: Path to game cycle database
        """
        self.db_path = db_path

    def load_directives(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        apply_season_offset: bool = True
    ) -> Optional[OwnerDirectives]:
        """
        Load owner directives with consistent error handling.

        Args:
            dynasty_id: Dynasty ID
            team_id: Team ID
            season: Current season
            apply_season_offset: If True, loads season+1 directives (for offseason stages).
                                 During offseason, directives are saved for "next season"
                                 so we need to load season+1.

        Returns:
            OwnerDirectives object or None if not found/error
        """
        try:
            # Create database connection using proper GameCycleDatabase instance
            # This fixes constructor bugs on lines 691, 1354, 1598, 1699 of offseason.py
            db = GameCycleDatabase(self.db_path)
            directives_api = OwnerDirectivesAPI(db)

            # Apply season offset if requested
            # Offseason stages need season+1 because directives are saved during
            # Owner Review for the NEXT season's offseason
            load_season = season + 1 if apply_season_offset else season

            # Load directives from database
            directives = directives_api.get_directives(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=load_season
            )

            return directives  # API already returns OwnerDirectives object or None

        except Exception as e:
            # Silent failure - return None so stages can continue without directives
            # Log for debugging but don't propagate exception
            print(f"[DirectiveLoader] Error loading directives for team {team_id}, "
                  f"season {season}: {e}")
            traceback.print_exc()
            return None

    def load_for_draft(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> Optional[DraftDirection]:
        """
        Load directives and convert to DraftDirection for draft stage.

        Args:
            dynasty_id: Dynasty ID
            team_id: Team ID
            season: Current season

        Returns:
            DraftDirection object or None
        """
        directives = self.load_directives(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            apply_season_offset=True
        )

        if directives:
            return directives.to_draft_direction()
        return None

    def load_for_fa(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> Optional[FAGuidance]:
        """
        Load directives and convert to FAGuidance for free agency stage.

        Args:
            dynasty_id: Dynasty ID
            team_id: Team ID
            season: Current season

        Returns:
            FAGuidance object or None
        """
        directives = self.load_directives(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            apply_season_offset=True
        )

        if directives:
            return directives.to_fa_guidance()
        return None

    def load_with_trust_gm(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> tuple[Optional[OwnerDirectives], bool]:
        """
        Load directives and return trust_gm flag.

        Convenience method for stages that need both directives and trust_gm flag.

        Args:
            dynasty_id: Dynasty ID
            team_id: Team ID
            season: Current season

        Returns:
            Tuple of (directives, trust_gm_flag)
            - directives: OwnerDirectives or None
            - trust_gm_flag: True if trust_gm enabled, False otherwise
        """
        directives = self.load_directives(dynasty_id, team_id, season)
        trust_gm = directives.trust_gm if directives else False
        return directives, trust_gm

    def save_directives(self, directives: OwnerDirectives) -> bool:
        """
        Save owner directives to the database.

        Args:
            directives: OwnerDirectives object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            db = GameCycleDatabase(self.db_path)
            directives_api = OwnerDirectivesAPI(db)
            return directives_api.save_directives(directives)
        except Exception as e:
            print(f"[DirectiveLoader] Error saving directives for team {directives.team_id}: {e}")
            traceback.print_exc()
            return False
