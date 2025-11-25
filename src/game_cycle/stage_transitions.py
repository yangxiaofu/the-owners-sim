"""
Stage Transitions - Logic for moving between stages.

Handles validation and side effects when transitioning from one stage to another.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .stage_definitions import Stage, StageType, SeasonPhase


@dataclass
class TransitionResult:
    """Result of a stage transition."""
    success: bool
    from_stage: Stage
    to_stage: Optional[Stage]
    message: str
    side_effects: List[str]


# Type alias for transition hooks
TransitionHook = Callable[[Stage, Stage], None]


class StageTransitionManager:
    """
    Manages transitions between stages.

    Handles:
    - Validation that a transition is allowed
    - Side effects that should happen on transition
    - Hooks for custom transition logic
    """

    def __init__(self):
        self._pre_hooks: Dict[StageType, List[TransitionHook]] = {}
        self._post_hooks: Dict[StageType, List[TransitionHook]] = {}

    def can_transition(self, from_stage: Stage, to_stage: Stage) -> tuple[bool, str]:
        """
        Check if a transition is valid.

        Args:
            from_stage: Current stage
            to_stage: Target stage

        Returns:
            Tuple of (is_valid, reason)
        """
        # Must complete current stage first
        if not from_stage.completed:
            return False, f"{from_stage.display_name} is not complete"

        # Validate stage ordering
        all_stages = list(StageType)
        from_index = all_stages.index(from_stage.stage_type)
        to_index = all_stages.index(to_stage.stage_type)

        # Normal forward progression
        if to_index == from_index + 1:
            return True, "Valid forward progression"

        # Skipping preseason is allowed
        if (from_stage.stage_type == StageType.PRESEASON_WEEK_3 and
                to_stage.stage_type == StageType.REGULAR_WEEK_1):
            return True, "Skipping to regular season"

        # Starting new season (from preseason to week 1 of next year)
        if from_stage.stage_type == StageType.OFFSEASON_PRESEASON:
            if to_stage.stage_type == StageType.REGULAR_WEEK_1:
                if to_stage.season_year == from_stage.season_year + 1:
                    return True, "Starting new season"
                return False, "New season must increment year"

        return False, f"Cannot transition from {from_stage.display_name} to {to_stage.display_name}"

    def execute_transition(
        self,
        from_stage: Stage,
        to_stage: Stage
    ) -> TransitionResult:
        """
        Execute a transition between stages.

        Args:
            from_stage: Current stage
            to_stage: Target stage

        Returns:
            TransitionResult with outcome
        """
        # Validate
        is_valid, reason = self.can_transition(from_stage, to_stage)
        if not is_valid:
            return TransitionResult(
                success=False,
                from_stage=from_stage,
                to_stage=None,
                message=reason,
                side_effects=[]
            )

        side_effects = []

        # Run pre-transition hooks
        for hook in self._pre_hooks.get(from_stage.stage_type, []):
            try:
                hook(from_stage, to_stage)
                side_effects.append(f"Pre-hook for {from_stage.stage_type.name}")
            except Exception as e:
                return TransitionResult(
                    success=False,
                    from_stage=from_stage,
                    to_stage=None,
                    message=f"Pre-hook failed: {e}",
                    side_effects=side_effects
                )

        # Execute built-in transition logic
        self._execute_builtin_transition(from_stage, to_stage, side_effects)

        # Run post-transition hooks
        for hook in self._post_hooks.get(to_stage.stage_type, []):
            try:
                hook(from_stage, to_stage)
                side_effects.append(f"Post-hook for {to_stage.stage_type.name}")
            except Exception as e:
                # Log but don't fail - transition already happened
                side_effects.append(f"Post-hook warning: {e}")

        return TransitionResult(
            success=True,
            from_stage=from_stage,
            to_stage=to_stage,
            message=f"Transitioned to {to_stage.display_name}",
            side_effects=side_effects
        )

    def register_pre_hook(self, stage: StageType, hook: TransitionHook) -> None:
        """Register a hook to run before leaving a stage."""
        if stage not in self._pre_hooks:
            self._pre_hooks[stage] = []
        self._pre_hooks[stage].append(hook)

    def register_post_hook(self, stage: StageType, hook: TransitionHook) -> None:
        """Register a hook to run after entering a stage."""
        if stage not in self._post_hooks:
            self._post_hooks[stage] = []
        self._post_hooks[stage].append(hook)

    def _execute_builtin_transition(
        self,
        from_stage: Stage,
        to_stage: Stage,
        side_effects: List[str]
    ) -> None:
        """Execute built-in transition logic based on stage types."""

        # Regular season complete -> Playoffs
        if (from_stage.stage_type == StageType.REGULAR_WEEK_18 and
                to_stage.stage_type == StageType.WILD_CARD):
            side_effects.append("Seeding playoff bracket")
            # TODO: Call playoff seeder

        # Super Bowl complete -> Offseason (Re-signing)
        if (from_stage.stage_type == StageType.SUPER_BOWL and
                to_stage.stage_type == StageType.OFFSEASON_RESIGNING):
            side_effects.append("Entering offseason")
            # TODO: Initialize offseason state

        # Preseason complete -> New Season
        if from_stage.stage_type == StageType.OFFSEASON_PRESEASON:
            side_effects.append("Starting new season")
            # TODO: Increment season year, reset stats, etc.


def get_transition_description(from_stage: StageType, to_stage: StageType) -> str:
    """Get a human-readable description of a transition."""
    descriptions = {
        (StageType.REGULAR_WEEK_18, StageType.WILD_CARD):
            "Regular season complete! The playoffs begin.",
        (StageType.WILD_CARD, StageType.DIVISIONAL):
            "Wild Card Weekend complete. On to the Divisional Round!",
        (StageType.DIVISIONAL, StageType.CONFERENCE_CHAMPIONSHIP):
            "Divisional Round complete. Conference Championships ahead!",
        (StageType.CONFERENCE_CHAMPIONSHIP, StageType.SUPER_BOWL):
            "Conference Champions crowned. Super Bowl time!",
        (StageType.SUPER_BOWL, StageType.OFFSEASON_RESIGNING):
            "A champion has been crowned! The offseason begins.",
        (StageType.OFFSEASON_RESIGNING, StageType.OFFSEASON_FREE_AGENCY):
            "Re-signing complete. Free agency opens!",
        (StageType.OFFSEASON_FREE_AGENCY, StageType.OFFSEASON_DRAFT):
            "Free agency complete. Time for the NFL Draft!",
        (StageType.OFFSEASON_DRAFT, StageType.OFFSEASON_ROSTER_CUTS):
            "Draft complete. Time to cut the roster to 53.",
        (StageType.OFFSEASON_ROSTER_CUTS, StageType.OFFSEASON_TRAINING_CAMP):
            "Roster cuts complete. Training camp begins!",
        (StageType.OFFSEASON_TRAINING_CAMP, StageType.OFFSEASON_PRESEASON):
            "Training camp complete. Preseason games begin!",
        (StageType.OFFSEASON_PRESEASON, StageType.REGULAR_WEEK_1):
            "A new season begins!",
    }

    return descriptions.get(
        (from_stage, to_stage),
        f"Moving from {from_stage.name} to {to_stage.name}"
    )