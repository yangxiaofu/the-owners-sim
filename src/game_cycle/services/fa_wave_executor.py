"""
FA Wave Executor - Orchestrator for wave-based free agency execution.

Part of Milestone 8: Free Agency Depth - Tollgate 3.

Design:
- Dependency Injection: FAWaveService passed to constructor (mockable for tests)
- Single Responsibility: Each method does one thing
- Structured Results: Dataclasses instead of dicts for type safety
- Event-Free Core: Business logic returns data, handler formats events
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .fa_wave_service import FAWaveService


class OfferOutcome(Enum):
    """Outcome of an offer submission attempt."""
    SUBMITTED = "submitted"
    DUPLICATE = "duplicate"
    CAP_EXCEEDED = "cap_exceeded"
    NOT_ALLOWED = "not_allowed"
    WITHDRAWN = "withdrawn"


@dataclass
class OfferResult:
    """Result of a single offer submission."""
    player_id: int
    outcome: OfferOutcome
    offer_id: Optional[int] = None
    error: Optional[str] = None


@dataclass
class SigningResult:
    """Result of a player signing."""
    player_id: int
    player_name: str
    team_id: int
    aav: int
    years: int
    is_surprise: bool = False


@dataclass
class WaveExecutionResult:
    """Complete result of executing one FA wave turn."""
    wave: int
    wave_name: str
    current_day: int
    days_in_wave: int
    wave_complete: bool
    is_fa_complete: bool

    offers_submitted: List[OfferResult] = field(default_factory=list)
    offers_withdrawn: List[int] = field(default_factory=list)
    ai_offers_made: int = 0
    surprises: List[SigningResult] = field(default_factory=list)
    signings: List[SigningResult] = field(default_factory=list)
    rejections: List[int] = field(default_factory=list)  # player_ids who rejected all
    pending_offers: int = 0


class FAWaveExecutor:
    """
    Orchestrates FA wave execution with injectable dependencies.

    This class wraps FAWaveService to provide:
    - Dependency injection for testability
    - Structured return types (dataclasses)
    - Focused, single-purpose methods
    - Event-free business logic (handler formats events)

    Usage:
        # Production
        executor = FAWaveExecutor.create(db_path, dynasty_id, season)
        result = executor.execute(user_team_id, submit_offers=[...])

        # Testing
        mock_service = Mock(spec=FAWaveService)
        executor = FAWaveExecutor(mock_service)
    """

    def __init__(self, wave_service: "FAWaveService"):
        """
        Initialize executor with wave service dependency.

        Args:
            wave_service: FAWaveService instance (injectable for testing)
        """
        self._wave_service = wave_service

    @classmethod
    def create(
        cls,
        db_path: str,
        dynasty_id: str,
        season: int
    ) -> "FAWaveExecutor":
        """
        Factory method for production use.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year

        Returns:
            FAWaveExecutor instance with real FAWaveService
        """
        from .fa_wave_service import FAWaveService
        wave_service = FAWaveService(db_path, dynasty_id, season)
        return cls(wave_service)

    # -------------------------------------------------------------------------
    # User Actions
    # -------------------------------------------------------------------------

    def submit_offer(
        self,
        player_id: int,
        team_id: int,
        aav: int,
        years: int,
        guaranteed: int,
        signing_bonus: int = 0
    ) -> OfferResult:
        """
        Submit a single offer to a free agent.

        Args:
            player_id: Player to offer
            team_id: Team making the offer
            aav: Average annual value
            years: Contract length
            guaranteed: Guaranteed money
            signing_bonus: Optional signing bonus

        Returns:
            OfferResult with outcome and optional offer_id or error
        """
        result = self._wave_service.submit_offer(
            player_id=player_id,
            team_id=team_id,
            aav=aav,
            years=years,
            guaranteed=guaranteed,
            signing_bonus=signing_bonus
        )

        if result.get("success"):
            return OfferResult(
                player_id=player_id,
                outcome=OfferOutcome.SUBMITTED,
                offer_id=result["offer_id"]
            )

        # Map error string to typed outcome
        error = result.get("error", "")
        error_lower = error.lower()

        if "duplicate" in error_lower or "already" in error_lower:
            outcome = OfferOutcome.DUPLICATE
        elif "cap" in error_lower or "space" in error_lower:
            outcome = OfferOutcome.CAP_EXCEEDED
        else:
            outcome = OfferOutcome.NOT_ALLOWED

        return OfferResult(
            player_id=player_id,
            outcome=outcome,
            error=error
        )

    def withdraw_offer(self, offer_id: int) -> bool:
        """
        Withdraw a pending offer.

        Args:
            offer_id: ID of offer to withdraw

        Returns:
            True if successfully withdrawn
        """
        return self._wave_service.withdraw_offer(offer_id)

    # -------------------------------------------------------------------------
    # AI Turn
    # -------------------------------------------------------------------------

    def process_ai_turn(
        self,
        user_team_id: int
    ) -> tuple[int, List[SigningResult]]:
        """
        Process AI offers and surprise signings.

        Args:
            user_team_id: User's team ID (excluded from AI processing)

        Returns:
            Tuple of (ai_offers_made, surprise_signings)
        """
        # Generate AI offers
        ai_result = self._wave_service.generate_ai_offers(user_team_id)
        ai_offers_made = ai_result.get("offers_made", 0)

        # Process surprise signings
        surprises_raw = self._wave_service.process_surprise_signings(user_team_id)
        surprises = [
            SigningResult(
                player_id=s["player_id"],
                player_name=s.get("player_name", f"Player {s['player_id']}"),
                team_id=s["team_id"],
                aav=s["aav"],
                years=0,  # Not tracked in surprise signings
                is_surprise=True
            )
            for s in surprises_raw
        ]

        return ai_offers_made, surprises

    # -------------------------------------------------------------------------
    # Wave Control
    # -------------------------------------------------------------------------

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance to next day within current wave.

        Returns:
            Updated wave state dict
        """
        return self._wave_service.advance_day()

    def advance_wave(
        self
    ) -> tuple[List[SigningResult], List[int], Optional[Dict[str, Any]]]:
        """
        Resolve all pending offers and advance to next wave.

        Returns:
            Tuple of (signings, rejected_player_ids, new_wave_state or None)
        """
        # Resolve all pending offers first
        resolution = self._wave_service.resolve_wave_offers()

        # Convert signings to dataclass
        signings = [
            SigningResult(
                player_id=s["player_id"],
                player_name=s.get("player_name", ""),
                team_id=s["team_id"],
                aav=s["aav"],
                years=s["years"],
                is_surprise=False
            )
            for s in resolution.get("signings", [])
        ]

        # Extract player IDs who rejected all offers
        rejected = [r["player_id"] for r in resolution.get("no_accepts", [])]

        # Advance to next wave
        try:
            new_state = self._wave_service.advance_wave()
        except ValueError:
            # Can't advance (e.g., Wave 3 → 4 requires Draft)
            # Mark current wave as complete so UI can detect it
            api = self._wave_service._get_wave_state_api()
            api.mark_wave_complete(self._wave_service._dynasty_id, self._wave_service._season)
            print(f"[DEBUG FAWaveExecutor] Wave marked complete (Draft required)")
            new_state = None

        return signings, rejected, new_state

    def enable_post_draft(self) -> Dict[str, Any]:
        """
        Enable post-draft wave (wave 4) after draft completes.

        Returns:
            Updated wave state dict
        """
        return self._wave_service.enable_post_draft_wave()

    # -------------------------------------------------------------------------
    # State Queries
    # -------------------------------------------------------------------------

    def get_wave_state(self) -> Dict[str, Any]:
        """Get current wave state."""
        return self._wave_service.get_wave_state()

    def get_wave_summary(self) -> Dict[str, Any]:
        """Get wave summary for UI display."""
        return self._wave_service.get_wave_summary()

    def is_fa_complete(self) -> bool:
        """Check if all FA waves are done."""
        return self._wave_service.is_fa_complete()

    def get_available_players(
        self,
        user_team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available players for current wave.

        Args:
            user_team_id: Optional user team ID for offer status

        Returns:
            List of player dicts with offer status
        """
        return self._wave_service.get_available_players_for_wave(
            user_team_id=user_team_id
        )

    def get_team_pending_offers(
        self,
        team_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get pending offers for a team.

        Args:
            team_id: Team ID

        Returns:
            List of offer dicts
        """
        return self._wave_service.get_team_pending_offers(team_id)

    # -------------------------------------------------------------------------
    # Full Execution
    # -------------------------------------------------------------------------

    def execute(
        self,
        user_team_id: int,
        submit_offers: Optional[List[Dict[str, Any]]] = None,
        withdraw_offers: Optional[List[int]] = None,
        advance_day: bool = False,
        advance_wave: bool = False,
        enable_post_draft: bool = False
    ) -> WaveExecutionResult:
        """
        Execute a complete FA turn with all actions.

        This is the main entry point that combines all operations
        into a single structured result.

        Args:
            user_team_id: User's team ID
            submit_offers: List of offer dicts with player_id, aav, years, etc.
            withdraw_offers: List of offer_ids to withdraw
            advance_day: Whether to advance to next day
            advance_wave: Whether to resolve offers and advance wave
            enable_post_draft: Whether to enable wave 4

        Returns:
            WaveExecutionResult with all turn data
        """
        submit_offers = submit_offers or []
        withdraw_offers = withdraw_offers or []

        # Get initial state
        state = self.get_wave_state()

        # 1. Process user offer submissions
        offer_results: List[OfferResult] = []
        for offer_data in submit_offers:
            result = self.submit_offer(
                player_id=offer_data["player_id"],
                team_id=user_team_id,
                aav=offer_data.get("aav", 0),
                years=offer_data.get("years", 1),
                guaranteed=offer_data.get("guaranteed", 0),
                signing_bonus=offer_data.get("signing_bonus", 0)
            )
            offer_results.append(result)

        # 2. Process offer withdrawals
        withdrawn: List[int] = []
        for offer_id in withdraw_offers:
            if self.withdraw_offer(offer_id):
                withdrawn.append(offer_id)

        # 3. AI turn (only if signing is allowed in current wave)
        ai_offers_made = 0
        surprises: List[SigningResult] = []
        if state.get("signing_allowed", False):
            ai_offers_made, surprises = self.process_ai_turn(user_team_id)

        # 4. Wave control (mutually exclusive - only one can happen)
        signings: List[SigningResult] = []
        rejections: List[int] = []

        if enable_post_draft:
            state = self.enable_post_draft()
        elif advance_wave:
            signings, rejections, new_state = self.advance_wave()
            print(f"[DEBUG FAWaveExecutor] advance_wave() returned: new_state={new_state}")
            if new_state is not None:
                state = new_state
            else:
                # advance_wave() returned None (e.g., can't advance Wave 3→4 without Draft)
                # Re-fetch current state to ensure consistency
                print(f"[WARNING FAWaveExecutor] advance_wave() returned None - re-fetching current state")
                state = self.get_wave_state()
            print(f"[DEBUG FAWaveExecutor] Final state: wave={state.get('current_wave')}, wave_name={state.get('wave_name')}, wave_complete={state.get('wave_complete')}")
        elif advance_day:
            state = self.advance_day()

        # Build final result with updated state
        summary = self.get_wave_summary()

        return WaveExecutionResult(
            wave=state.get("current_wave", 0),
            wave_name=state.get("wave_name", "Unknown"),
            current_day=state.get("current_day", 1),
            days_in_wave=state.get("days_in_wave", 1),
            wave_complete=state.get("wave_complete", False),
            is_fa_complete=self.is_fa_complete(),
            offers_submitted=offer_results,
            offers_withdrawn=withdrawn,
            ai_offers_made=ai_offers_made,
            surprises=surprises,
            signings=signings,
            rejections=rejections,
            pending_offers=summary.get("pending_offers", 0)
        )