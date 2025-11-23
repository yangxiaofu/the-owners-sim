"""
Team Context Service

Provides centralized team context building for GM AI decision-making.
Used across free agency, draft, trades, and roster management.
"""

from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING
from database.api import DatabaseAPI
from salary_cap.cap_calculator import CapCalculator
from transactions.personality_modifiers import TeamContext

if TYPE_CHECKING:
    from offseason.team_needs_analyzer import TeamNeedsAnalyzer


class TeamContextService:
    """
    Service for building TeamContext objects from database state.

    Centralizes team situation queries for use across all GM AI systems.
    Provides reusable context building to avoid duplication.
    """

    def __init__(self, database_path: str, dynasty_id: str):
        """
        Initialize TeamContextService.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.db_api = DatabaseAPI(database_path)
        self.cap_calc = CapCalculator(database_path)

    def get_team_record(self, team_id: int, season: int) -> Dict[str, int]:
        """
        Get team's win-loss record for specified season.

        Args:
            team_id: Team ID (1-32)
            season: Season year (e.g., 2024)

        Returns:
            Dict with 'wins', 'losses', 'ties' keys
        """
        standings = self.db_api.get_standings(
            dynasty_id=self.dynasty_id,
            season=season,
            season_type="regular_season"
        )

        # Extract team's record from standings
        for team_standing in standings:
            if team_standing['team_id'] == team_id:
                return {
                    'wins': team_standing.get('wins', 0),
                    'losses': team_standing.get('losses', 0),
                    'ties': team_standing.get('ties', 0)
                }

        # Fallback if team not found (preseason scenario)
        return {'wins': 0, 'losses': 0, 'ties': 0}

    def get_team_cap_space(self, team_id: int, season: int, roster_mode: str = "offseason") -> int:
        """
        Get team's available cap space.

        Args:
            team_id: Team ID (1-32)
            season: Season year (e.g., 2024)
            roster_mode: "offseason" (top-51) or "regular_season" (53-man)

        Returns:
            Available cap space in dollars
        """
        cap_space = self.cap_calc.calculate_team_cap_space(
            team_id=team_id,
            season=season,
            dynasty_id=self.dynasty_id,
            roster_mode=roster_mode
        )

        return cap_space

    def build_team_context(
        self,
        team_id: int,
        season: int,
        needs_analyzer: Optional[TeamNeedsAnalyzer] = None,
        is_offseason: bool = True,
        roster_mode: str = "offseason"
    ) -> TeamContext:
        """
        Build complete team context from database state.

        Aggregates team situation data for GM decision-making:
        - Win-loss record (competitiveness)
        - Cap space (financial flexibility)
        - Top positional needs (roster gaps)

        Args:
            team_id: Team ID (1-32)
            season: Season year (e.g., 2024)
            needs_analyzer: Optional TeamNeedsAnalyzer for positional needs
            is_offseason: Whether this is offseason context
            roster_mode: "offseason" or "regular_season" for cap calculations

        Returns:
            TeamContext with current team situation
        """
        # 1. Get team record
        team_record = self.get_team_record(team_id, season)

        # 2. Get cap space
        cap_space = self.get_team_cap_space(team_id, season, roster_mode)

        # 3. Get team needs (if analyzer provided)
        top_needs = []
        if needs_analyzer:
            needs = needs_analyzer.analyze_team_needs(
                team_id=team_id,
                season=season,
                include_future_contracts=True
            )
            top_needs = [need['position'] for need in needs[:3]]

        # 4. Calculate cap percentage (2024 cap: $255.5M)
        # TODO: Query actual cap from database instead of hardcoding
        salary_cap = 255_500_000
        cap_percentage = cap_space / salary_cap if cap_space > 0 else 0.0

        # 5. Build TeamContext
        return TeamContext(
            team_id=team_id,
            season=season,
            wins=team_record['wins'],
            losses=team_record['losses'],
            cap_space=cap_space,
            cap_percentage=cap_percentage,
            top_needs=top_needs,
            is_offseason=is_offseason
        )