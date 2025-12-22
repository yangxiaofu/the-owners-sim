"""
Stage Action Mapping - Maps game stages to suggested next actions.

Provides context-aware action button text and navigation targets for each stage.
"""

from typing import Dict

from game_cycle.stage_definitions import StageType


def _create_regular_season_actions() -> Dict[StageType, dict]:
    """Generate action configs for all 18 regular season weeks."""
    base_config = {
        "text": "View Schedule ▶",
        "target_view": "season",
        "category": "Game Day",
        "style": "primary",
    }

    return {
        getattr(StageType, f"REGULAR_WEEK_{week}"): base_config.copy()
        for week in range(1, 19)
    }


def _create_playoff_actions() -> Dict[StageType, dict]:
    """Generate action configs for playoff stages."""
    stages = {
        StageType.WILD_CARD: "View Wild Card ▶",
        StageType.DIVISIONAL: "View Divisional ▶",
        StageType.CONFERENCE_CHAMPIONSHIP: "View Conference Finals ▶",
        StageType.SUPER_BOWL: "View Super Bowl ▶",
    }

    base_config = {
        "target_view": "playoffs",
        "category": "Game Day",
        "style": "urgent",
    }

    return {
        stage_type: {**base_config, "text": text}
        for stage_type, text in stages.items()
    }


def _create_offseason_actions() -> Dict[StageType, dict]:
    """Generate action configs for standard offseason stages."""
    stages = {
        "FRANCHISE_TAG": "Franchise Tag ▶",
        "RESIGNING": "Re-signing ▶",
        "FREE_AGENCY": "Free Agency ▶",
        "TRADING": "Trading ▶",
        "DRAFT": "Draft ▶",
        "TRAINING_CAMP": "Training Camp ▶",
        "PRESEASON_W1": "Preseason Week 1 ▶",
        "PRESEASON_W2": "Preseason Week 2 ▶",
        "PRESEASON_W3": "Final Roster Cuts ▶",  # W3 has cuts (90→53)
        "WAIVER_WIRE": "Waiver Wire ▶",
    }

    base_config = {
        "target_view": "offseason_overview",
        "category": "Front Office",
        "style": "action",
    }

    return {
        getattr(StageType, f"OFFSEASON_{stage}"): {
            **base_config,
            "text": text,
            "style": "urgent" if stage == "DRAFT" else "action"
        }
        for stage, text in stages.items()
    }


# Complete mapping of all stage types to suggested actions
STAGE_ACTIONS = {
    **_create_regular_season_actions(),  # Generates all 18 regular season weeks
    **_create_playoff_actions(),          # Generates all 4 playoff stages
    **_create_offseason_actions(),        # Generates all 10 standard offseason stages
    # Special offseason stages (don't follow standard pattern)
    StageType.OFFSEASON_HONORS: {
        "text": "Awards ▶",
        "target_view": "season_recap",
        "category": "Offseason",
        "style": "action",
    },
    StageType.OFFSEASON_OWNER: {
        "text": "Review Proposals ▶",
        "target_view": "owner",
        "category": "Front Office",
        "style": "urgent",
    },
}


def get_action_for_stage(stage_type: StageType) -> dict:
    """
    Get action configuration for a stage.

    Args:
        stage_type: The stage type to get action for

    Returns:
        Dictionary with keys:
            - text: Button text (e.g., "Game Day ▶")
            - target_view: View key to navigate to (e.g., "season")
            - category: Category name (e.g., "Game Day")
            - style: Button style ("primary", "urgent", "action")
    """
    return STAGE_ACTIONS.get(
        stage_type,
        {
            "text": "Continue ▶",
            "target_view": "season",
            "category": "Game Day",
            "style": "primary",
        },
    )


def get_badge_for_stage(stage_type: StageType) -> str:
    """
    Get category badge type for a stage.

    Args:
        stage_type: The stage type to get badge for

    Returns:
        Badge type: "urgent", "action", or None
    """
    action = get_action_for_stage(stage_type)
    style = action.get("style")

    if style == "urgent":
        return "urgent"
    elif style == "action":
        return "action"
    return None


def get_simulate_button_text(stage) -> str:
    """
    Get simulation button text for a stage.

    Returns action-oriented text (e.g., "Simulate Games ▶", "Simulate Wild Card ▶").

    Args:
        stage: Stage object with stage_type, week_number, and phase attributes

    Returns:
        Button text string
    """
    from game_cycle.stage_definitions import SeasonPhase

    # Regular season
    if stage.week_number and stage.week_number <= 18:
        return "Simulate Games ▶"

    # Playoffs - extract base name from navigation text and prefix with "Simulate"
    if stage.phase == SeasonPhase.PLAYOFFS:
        action_config = get_action_for_stage(stage.stage_type)
        nav_text = action_config.get("text", "")

        # Convert "View Wild Card ▶" → "Simulate Wild Card ▶"
        if nav_text.startswith("View "):
            return nav_text.replace("View ", "Simulate ", 1)

        # Fallback for missing mapping
        return "Simulate Playoff ▶"

    # Offseason
    return "Continue ▶"


def get_button_text(stage_type: StageType) -> str:
    """Get navigation button text for a stage."""
    action = get_action_for_stage(stage_type)
    return action.get("text", "Continue ▶")


def get_target_view(stage_type: StageType) -> str:
    """Get target view key for a stage."""
    action = get_action_for_stage(stage_type)
    return action.get("target_view", "season")


def get_button_style(stage_type: StageType) -> str:
    """Get button style (primary/urgent/action)."""
    action = get_action_for_stage(stage_type)
    return action.get("style", "primary")
