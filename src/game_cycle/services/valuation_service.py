"""
Valuation Service - Bridge between game state and ContractValuationEngine.

Provides contract valuation by building context from database state
and delegating to the sophisticated multi-factor valuation engine.

Part of Milestone 14: Contract Valuation Engine.
"""

import sqlite3
from typing import Dict, Any, Optional, TYPE_CHECKING

from contract_valuation.engine import ContractValuationEngine
from contract_valuation.models import ValuationResult
from contract_valuation.context import (
    ValuationContext,
    OwnerContext,
    JobSecurityContext,
)
from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.staff_api import StaffAPI
from game_cycle.database.standings_api import StandingsAPI
from game_cycle.database.owner_directives_api import OwnerDirectivesAPI

if TYPE_CHECKING:
    from team_management.gm_archetype import GMArchetype


class ValuationService:
    """
    Bridge between game services and ContractValuationEngine.

    Builds context from database (cap, season, owner directives, job security)
    and delegates valuation to the engine. Provides a simple interface for
    services that need to value players for contract purposes.

    Usage:
        service = ValuationService(conn, dynasty_id)
        result = service.valuate_player(player_data, team_id, gm_archetype)
        aav = result.offer.aav
        years = result.offer.years
    """

    # Default salary cap for 2025 if not specified
    DEFAULT_SALARY_CAP = 255_000_000

    def __init__(
        self,
        conn: sqlite3.Connection,
        dynasty_id: str,
        season: Optional[int] = None,
    ):
        """
        Initialize valuation service.

        Args:
            conn: Database connection
            dynasty_id: Dynasty identifier for data isolation
            season: Optional season year (default: current from DB)
        """
        self._conn = conn
        self._dynasty_id = dynasty_id
        self._season = season
        self._engine = ContractValuationEngine()

        # Initialize database APIs
        self._db = GameCycleDatabase(conn)
        self._staff_api = StaffAPI(self._db)
        self._standings_api = StandingsAPI(conn, dynasty_id)
        self._directives_api = OwnerDirectivesAPI(self._db)

        # Cache for context objects (avoid repeated DB queries)
        self._context_cache: Dict[str, Any] = {}

    def valuate_player(
        self,
        player_data: Dict[str, Any],
        team_id: int,
        gm_archetype: Optional["GMArchetype"] = None,
    ) -> ValuationResult:
        """
        Valuate a player for contract purposes.

        Args:
            player_data: Player information dictionary. Must include:
                - position: Player position (e.g., "QB", "WR")
                - overall_rating: Overall rating (0-99)
                - age: Player age
                Optional fields used if available:
                - stats: Season statistics
                - attributes: Scouting attributes

            team_id: Team making the offer (1-32)
            gm_archetype: Optional GM archetype for style weighting

        Returns:
            ValuationResult with offer, factor breakdown, and audit trail
        """
        valuation_context = self._get_valuation_context()
        owner_context = self._get_owner_context(team_id)

        return self._engine.valuate(
            player_data=player_data,
            valuation_context=valuation_context,
            owner_context=owner_context,
            gm_archetype=gm_archetype,
        )

    def valuate_batch(
        self,
        players: list[Dict[str, Any]],
        team_id: int,
        gm_archetype: Optional["GMArchetype"] = None,
    ) -> list[ValuationResult]:
        """
        Valuate multiple players efficiently.

        Args:
            players: List of player data dictionaries
            team_id: Team making the offers (1-32)
            gm_archetype: Optional GM archetype for style weighting

        Returns:
            List of ValuationResult objects in same order as input
        """
        valuation_context = self._get_valuation_context()
        owner_context = self._get_owner_context(team_id)

        return self._engine.valuate_batch(
            players=players,
            valuation_context=valuation_context,
            owner_context=owner_context,
            gm_archetype=gm_archetype,
        )

    def _get_valuation_context(self) -> ValuationContext:
        """
        Get or build valuation context from database.

        Returns:
            ValuationContext with current cap/season info
        """
        cache_key = "valuation_context"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        # Get season from DB if not specified
        season = self._season or self._get_current_season()

        # Get salary cap from dynasty settings (fallback to default)
        salary_cap = self._get_salary_cap() or self.DEFAULT_SALARY_CAP

        # Use default 2025 market rates
        context = ValuationContext.create_default_2025()
        # Override with actual season/cap
        context = ValuationContext(
            salary_cap=salary_cap,
            season=season,
            position_market_rates=context.position_market_rates,
        )

        self._context_cache[cache_key] = context
        return context

    def _get_owner_context(self, team_id: int) -> OwnerContext:
        """
        Build owner context from database for specific team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            OwnerContext with job security, philosophy, constraints
        """
        cache_key = f"owner_context_{team_id}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        # Get owner directives
        directives = self._get_owner_directives(team_id)

        # Get job security from staff tenure and performance
        job_security = self._calculate_job_security(team_id)

        # Build context
        if directives:
            context = OwnerContext.from_owner_directives(directives, job_security)
        else:
            # Default context if no directives set
            context = OwnerContext(
                dynasty_id=self._dynasty_id,
                team_id=team_id,
                job_security=job_security,
                owner_philosophy="balanced",
                team_philosophy="maintain",
                win_now_mode=False,
                max_contract_years=5,
                max_guaranteed_pct=0.60,
            )

        self._context_cache[cache_key] = context
        return context

    def _calculate_job_security(self, team_id: int) -> JobSecurityContext:
        """
        Calculate GM job security from staff tenure and team performance.

        Args:
            team_id: Team ID (1-32)

        Returns:
            JobSecurityContext with pressure factors
        """
        season = self._season or self._get_current_season()

        # Get staff assignment for tenure
        tenure_years = 3  # Default
        try:
            staff = self._staff_api.get_staff_assignment(
                self._dynasty_id, team_id, season
            )
            if staff and staff.get('gm'):
                gm = staff['gm']
                hire_season = gm.hire_season if hasattr(gm, 'hire_season') else season
                tenure_years = max(0, season - hire_season)
        except Exception:
            pass

        # Get recent win percentage from standings
        recent_win_pct = 0.50  # Default
        playoff_appearances = 0
        try:
            # Get last 2 seasons of standings
            for s in [season - 1, season - 2]:
                standings = self._standings_api.get_team_record(team_id, s)
                if standings:
                    wins = standings.get('wins', 0)
                    losses = standings.get('losses', 0)
                    total = wins + losses
                    if total > 0:
                        recent_win_pct = wins / total
                    # Check if made playoffs
                    if standings.get('playoff_seed'):
                        playoff_appearances += 1
        except Exception:
            pass

        # Owner patience (default balanced, could come from owner profile later)
        owner_patience = 0.50

        return JobSecurityContext(
            tenure_years=tenure_years,
            playoff_appearances=playoff_appearances,
            recent_win_pct=recent_win_pct,
            owner_patience=owner_patience,
        )

    def _get_owner_directives(self, team_id: int):
        """Get owner directives from database."""
        season = self._season or self._get_current_season()
        try:
            return self._directives_api.get_directives(
                self._dynasty_id, team_id, season
            )
        except Exception:
            return None

    def _get_current_season(self) -> int:
        """Get current season from database."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                """SELECT season FROM dynasty_state
                   WHERE dynasty_id = ?""",
                (self._dynasty_id,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        except Exception:
            pass
        return 2025  # Default

    def _get_salary_cap(self) -> Optional[int]:
        """Get salary cap from database."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                """SELECT salary_cap FROM dynasty_settings
                   WHERE dynasty_id = ?""",
                (self._dynasty_id,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        except Exception:
            pass
        return None

    def clear_cache(self):
        """Clear context cache (call if database state changes)."""
        self._context_cache.clear()
