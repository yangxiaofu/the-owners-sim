"""
Phase Transition Triggers

Game-based transition logic that determines when NFL season phases should change
based on actual game completions rather than calendar dates.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from .season_phase_tracker import (
    SeasonPhase, TransitionType, GameCompletionEvent, PhaseTransition
)
from .date_models import Date


class TriggerConditionType(Enum):
    """Types of conditions that can trigger phase transitions."""
    GAME_COUNT_THRESHOLD = "game_count_threshold"
    SPECIFIC_GAME_TYPE = "specific_game_type"
    WEEK_COMPLETION = "week_completion"
    PERCENTAGE_COMPLETE = "percentage_complete"
    CUSTOM_CONDITION = "custom_condition"


@dataclass
class TriggerCondition:
    """Defines a condition that must be met for a phase transition."""
    condition_type: TriggerConditionType
    description: str
    checker: Callable[[List[GameCompletionEvent], Dict[str, Any]], bool]
    metadata: Dict[str, Any]


class TransitionTrigger(ABC):
    """
    Abstract base class for phase transition triggers.
    Each trigger defines the conditions for transitioning between specific phases.
    """

    def __init__(self, from_phase: SeasonPhase, to_phase: SeasonPhase):
        """
        Initialize transition trigger.

        Args:
            from_phase: Source phase for the transition
            to_phase: Target phase for the transition
        """
        self.from_phase = from_phase
        self.to_phase = to_phase
        self.conditions: List[TriggerCondition] = []
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    def check_trigger(self, completed_games: List[GameCompletionEvent],
                     games_by_type: Dict[str, List[GameCompletionEvent]],
                     current_state: Dict[str, Any]) -> Optional[PhaseTransition]:
        """
        Check if this trigger's conditions are met.

        Args:
            completed_games: All completed games
            games_by_type: Games organized by type
            current_state: Current tracker state

        Returns:
            PhaseTransition if triggered, None otherwise
        """
        pass

    def add_condition(self, condition: TriggerCondition) -> None:
        """Add a condition to this trigger."""
        self.conditions.append(condition)

    def evaluate_conditions(self, completed_games: List[GameCompletionEvent],
                          games_by_type: Dict[str, List[GameCompletionEvent]]) -> bool:
        """Evaluate all conditions for this trigger."""
        for condition in self.conditions:
            try:
                if not condition.checker(completed_games, games_by_type):
                    return False
            except Exception:
                # If condition check fails, assume condition not met
                return False
        return True


class PreseasonToRegularSeasonTrigger(TransitionTrigger):
    """Trigger for transitioning from preseason to regular season."""

    def __init__(self):
        super().__init__(SeasonPhase.PRESEASON, SeasonPhase.REGULAR_SEASON)
        self.metadata = {
            "description": "Triggered by first Week 1 regular season game",
            "typical_timing": "Early September",
            "trigger_type": "first_game_kickoff"
        }

        # Add condition: First regular season game starts
        self.add_condition(TriggerCondition(
            condition_type=TriggerConditionType.SPECIFIC_GAME_TYPE,
            description="First regular season game of Week 1",
            checker=self._check_first_regular_game,
            metadata={"week": 1, "game_type": "regular"}
        ))

    def check_trigger(self, completed_games: List[GameCompletionEvent],
                     games_by_type: Dict[str, List[GameCompletionEvent]],
                     current_state: Dict[str, Any]) -> Optional[PhaseTransition]:
        """Check if first regular season game has been completed."""
        regular_games = games_by_type.get("regular", [])

        # Look for any Week 1 regular season game
        for game in regular_games:
            if game.week == 1:
                return PhaseTransition(
                    transition_type=TransitionType.REGULAR_SEASON_START,
                    from_phase=self.from_phase,
                    to_phase=self.to_phase,
                    trigger_date=game.completion_date,
                    trigger_event=game,
                    metadata={
                        "trigger": "first_regular_season_game",
                        "triggering_game": game.game_id,
                        "week": game.week
                    }
                )

        return None

    def _check_first_regular_game(self, completed_games: List[GameCompletionEvent],
                                 games_by_type: Dict[str, List[GameCompletionEvent]]) -> bool:
        """Check if the first regular season game has been played."""
        regular_games = games_by_type.get("regular", [])
        return any(game.week == 1 for game in regular_games)


class RegularSeasonToPlayoffsTrigger(TransitionTrigger):
    """Trigger for transitioning from regular season to playoffs."""

    TOTAL_REGULAR_SEASON_GAMES = 272  # 32 teams × 17 games ÷ 2

    def __init__(self):
        super().__init__(SeasonPhase.REGULAR_SEASON, SeasonPhase.PLAYOFFS)
        self.metadata = {
            "description": "Triggered when all 272 regular season games are complete",
            "typical_timing": "Early January after Week 18",
            "trigger_type": "season_completion"
        }

        # Add condition: All regular season games complete
        self.add_condition(TriggerCondition(
            condition_type=TriggerConditionType.GAME_COUNT_THRESHOLD,
            description="All 272 regular season games completed",
            checker=self._check_regular_season_complete,
            metadata={"total_games": self.TOTAL_REGULAR_SEASON_GAMES}
        ))

    def check_trigger(self, completed_games: List[GameCompletionEvent],
                     games_by_type: Dict[str, List[GameCompletionEvent]],
                     current_state: Dict[str, Any]) -> Optional[PhaseTransition]:
        """Check if all regular season games are complete."""
        regular_games = games_by_type.get("regular", [])

        if len(regular_games) >= self.TOTAL_REGULAR_SEASON_GAMES:
            # Find the last completed regular season game
            last_game = max(regular_games, key=lambda g: g.completion_time)

            return PhaseTransition(
                transition_type=TransitionType.PLAYOFFS_START,
                from_phase=self.from_phase,
                to_phase=self.to_phase,
                trigger_date=last_game.completion_date,
                trigger_event=last_game,
                metadata={
                    "trigger": "regular_season_complete",
                    "total_regular_games": len(regular_games),
                    "last_game": last_game.game_id,
                    "last_week": max(game.week for game in regular_games)
                }
            )

        return None

    def _check_regular_season_complete(self, completed_games: List[GameCompletionEvent],
                                     games_by_type: Dict[str, List[GameCompletionEvent]]) -> bool:
        """Check if all regular season games are complete."""
        regular_games = games_by_type.get("regular", [])
        return len(regular_games) >= self.TOTAL_REGULAR_SEASON_GAMES


class PlayoffsToOffseasonTrigger(TransitionTrigger):
    """Trigger for transitioning from playoffs to offseason."""

    def __init__(self):
        super().__init__(SeasonPhase.PLAYOFFS, SeasonPhase.OFFSEASON)
        self.metadata = {
            "description": "Triggered when Super Bowl is completed",
            "typical_timing": "Mid-February",
            "trigger_type": "championship_complete"
        }

        # Add condition: Super Bowl completed
        self.add_condition(TriggerCondition(
            condition_type=TriggerConditionType.SPECIFIC_GAME_TYPE,
            description="Super Bowl completed",
            checker=self._check_super_bowl_complete,
            metadata={"game_type": "super_bowl"}
        ))

    def check_trigger(self, completed_games: List[GameCompletionEvent],
                     games_by_type: Dict[str, List[GameCompletionEvent]],
                     current_state: Dict[str, Any]) -> Optional[PhaseTransition]:
        """Check if Super Bowl has been completed."""
        super_bowl_games = games_by_type.get("super_bowl", [])

        if super_bowl_games:
            super_bowl = super_bowl_games[0]  # There should only be one

            return PhaseTransition(
                transition_type=TransitionType.OFFSEASON_START,
                from_phase=self.from_phase,
                to_phase=self.to_phase,
                trigger_date=super_bowl.completion_date,
                trigger_event=super_bowl,
                metadata={
                    "trigger": "super_bowl_complete",
                    "super_bowl_game": super_bowl.game_id,
                    "champion_determination": "complete"
                }
            )

        return None

    def _check_super_bowl_complete(self, completed_games: List[GameCompletionEvent],
                                  games_by_type: Dict[str, List[GameCompletionEvent]]) -> bool:
        """Check if Super Bowl has been completed."""
        super_bowl_games = games_by_type.get("super_bowl", [])
        return len(super_bowl_games) >= 1


class OffseasonToPreseasonTrigger(TransitionTrigger):
    """Trigger for transitioning from offseason to preseason."""

    def __init__(self):
        super().__init__(SeasonPhase.OFFSEASON, SeasonPhase.PRESEASON)
        self.metadata = {
            "description": "Triggered by first preseason game",
            "typical_timing": "Early August",
            "trigger_type": "preseason_start"
        }

        # Add condition: First preseason game
        self.add_condition(TriggerCondition(
            condition_type=TriggerConditionType.SPECIFIC_GAME_TYPE,
            description="First preseason game played",
            checker=self._check_first_preseason_game,
            metadata={"game_type": "preseason"}
        ))

    def check_trigger(self, completed_games: List[GameCompletionEvent],
                     games_by_type: Dict[str, List[GameCompletionEvent]],
                     current_state: Dict[str, Any]) -> Optional[PhaseTransition]:
        """Check if first preseason game has been completed."""
        preseason_games = games_by_type.get("preseason", [])

        if preseason_games:
            first_preseason = min(preseason_games, key=lambda g: g.completion_time)

            return PhaseTransition(
                transition_type=TransitionType.SEASON_START,
                from_phase=self.from_phase,
                to_phase=self.to_phase,
                trigger_date=first_preseason.completion_date,
                trigger_event=first_preseason,
                metadata={
                    "trigger": "first_preseason_game",
                    "triggering_game": first_preseason.game_id,
                    "new_season_start": True
                }
            )

        return None

    def _check_first_preseason_game(self, completed_games: List[GameCompletionEvent],
                                   games_by_type: Dict[str, List[GameCompletionEvent]]) -> bool:
        """Check if any preseason game has been played."""
        preseason_games = games_by_type.get("preseason", [])
        return len(preseason_games) > 0


class TransitionTriggerManager:
    """
    Manages all phase transition triggers and evaluates them for phase changes.
    """

    def __init__(self):
        """Initialize with all standard NFL phase transition triggers."""
        self.triggers: List[TransitionTrigger] = [
            OffseasonToPreseasonTrigger(),
            PreseasonToRegularSeasonTrigger(),
            RegularSeasonToPlayoffsTrigger(),
            PlayoffsToOffseasonTrigger()
        ]

        # Create trigger lookup by phase pair
        self.trigger_map: Dict[tuple, TransitionTrigger] = {}
        for trigger in self.triggers:
            self.trigger_map[(trigger.from_phase, trigger.to_phase)] = trigger

    def check_all_triggers(self, current_phase: SeasonPhase,
                          completed_games: List[GameCompletionEvent],
                          games_by_type: Dict[str, List[GameCompletionEvent]],
                          current_state: Dict[str, Any]) -> Optional[PhaseTransition]:
        """
        Check all applicable triggers for the current phase.

        Args:
            current_phase: Current season phase
            completed_games: All completed games
            games_by_type: Games organized by type
            current_state: Current tracker state

        Returns:
            PhaseTransition if any trigger activates, None otherwise
        """
        # Find triggers that can activate from the current phase
        applicable_triggers = [t for t in self.triggers if t.from_phase == current_phase]

        for trigger in applicable_triggers:
            transition = trigger.check_trigger(completed_games, games_by_type, current_state)
            if transition:
                return transition

        return None

    def get_next_transition_info(self, current_phase: SeasonPhase) -> Dict[str, Any]:
        """
        Get information about the next possible transition from current phase.

        Args:
            current_phase: Current season phase

        Returns:
            Information about the next transition
        """
        applicable_triggers = [t for t in self.triggers if t.from_phase == current_phase]

        if not applicable_triggers:
            return {"next_transition": "none", "description": "No transitions available"}

        # Assume only one trigger per phase (typical for NFL)
        trigger = applicable_triggers[0]

        return {
            "next_transition": trigger.to_phase.value,
            "description": trigger.metadata.get("description", "Unknown transition"),
            "typical_timing": trigger.metadata.get("typical_timing", "Unknown timing"),
            "trigger_type": trigger.metadata.get("trigger_type", "Unknown trigger"),
            "conditions": [
                {
                    "type": cond.condition_type.value,
                    "description": cond.description,
                    "metadata": cond.metadata
                }
                for cond in trigger.conditions
            ]
        }

    def add_custom_trigger(self, trigger: TransitionTrigger) -> None:
        """Add a custom transition trigger."""
        self.triggers.append(trigger)
        self.trigger_map[(trigger.from_phase, trigger.to_phase)] = trigger

    def get_trigger_for_phases(self, from_phase: SeasonPhase,
                              to_phase: SeasonPhase) -> Optional[TransitionTrigger]:
        """Get the trigger for a specific phase transition."""
        return self.trigger_map.get((from_phase, to_phase))