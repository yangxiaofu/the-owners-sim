"""Tests for stage action mapping."""

import pytest
from game_cycle.stage_definitions import StageType, Stage, SeasonPhase
from game_cycle_ui.widgets.stage_action_mapping import (
    STAGE_ACTIONS,
    get_action_for_stage,
    get_badge_for_stage,
)


def get_simulate_button_text(stage: Stage) -> str:
    """
    Helper to get simulate button text for testing.

    This mimics the logic in owner_flow_guidance.py for button text generation.
    """
    if stage.phase == SeasonPhase.REGULAR_SEASON:
        return "Simulate Games ▶"
    elif stage.phase == SeasonPhase.PLAYOFFS:
        # Format: "Simulate [Round Name] ▶"
        round_name = stage.display_name
        return f"Simulate {round_name} ▶"
    else:
        return "Continue ▶"


def get_button_text(stage_type: StageType) -> str:
    """Get navigation button text for a stage type."""
    return get_action_for_stage(stage_type)["text"]


def get_target_view(stage_type: StageType) -> str:
    """Get target view for a stage type."""
    return get_action_for_stage(stage_type)["target_view"]


def get_button_style(stage_type: StageType) -> str:
    """Get button style for a stage type."""
    return get_action_for_stage(stage_type)["style"]


class TestSimulateButtonText:
    """Tests for get_simulate_button_text() helper."""

    def test_regular_season_week(self):
        """Regular season should return 'Simulate Games ▶'."""
        stage = Stage(
            stage_type=StageType.REGULAR_WEEK_1,
            season_year=2024,
            completed=False
        )
        assert get_simulate_button_text(stage) == "Simulate Games ▶"

    def test_playoff_wild_card(self):
        """Wild Card should return 'Simulate Wild Card ▶'."""
        stage = Stage(
            stage_type=StageType.WILD_CARD,
            season_year=2024,
            completed=False
        )
        assert get_simulate_button_text(stage) == "Simulate Wild Card ▶"

    def test_playoff_super_bowl(self):
        """Super Bowl should return 'Simulate Super Bowl ▶'."""
        stage = Stage(
            stage_type=StageType.SUPER_BOWL,
            season_year=2024,
            completed=False
        )
        assert get_simulate_button_text(stage) == "Simulate Super Bowl ▶"

    def test_offseason_stage(self):
        """Offseason stages should return 'Continue ▶'."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_HONORS,
            season_year=2024,
            completed=False
        )
        assert get_simulate_button_text(stage) == "Continue ▶"


class TestAccessorFunctions:
    """Tests for accessor functions."""

    def test_get_button_text(self):
        """get_button_text should return navigation button text."""
        text = get_button_text(StageType.REGULAR_WEEK_1)
        assert text == "View Schedule ▶"

    def test_get_target_view(self):
        """get_target_view should return target view key."""
        view = get_target_view(StageType.REGULAR_WEEK_1)
        assert view == "season"

    def test_get_button_style(self):
        """get_button_style should return button style."""
        style = get_button_style(StageType.REGULAR_WEEK_1)
        assert style == "primary"

    def test_get_badge_for_stage_urgent(self):
        """get_badge_for_stage should return 'urgent' for urgent stages."""
        badge = get_badge_for_stage(StageType.WILD_CARD)
        assert badge == "urgent"

    def test_get_badge_for_stage_action(self):
        """get_badge_for_stage should return 'action' for action stages."""
        badge = get_badge_for_stage(StageType.OFFSEASON_HONORS)
        assert badge == "action"

    def test_get_badge_for_stage_primary(self):
        """get_badge_for_stage should return None for primary stages."""
        badge = get_badge_for_stage(StageType.REGULAR_WEEK_1)
        assert badge is None


class TestRegularSeasonMapping:
    """Tests for regular season stage mappings."""

    def test_all_18_weeks_mapped(self):
        """All 18 regular season weeks should have mappings."""
        for week in range(1, 19):
            stage_type = StageType.get_regular_season_week(week)
            assert stage_type in STAGE_ACTIONS

    def test_all_weeks_have_correct_text(self):
        """All regular season weeks should have 'View Schedule ▶' text."""
        for week in range(1, 19):
            stage_type = StageType.get_regular_season_week(week)
            text = get_button_text(stage_type)
            assert text == "View Schedule ▶"

    def test_all_weeks_target_season_view(self):
        """All regular season weeks should target 'season' view."""
        for week in range(1, 19):
            stage_type = StageType.get_regular_season_week(week)
            view = get_target_view(stage_type)
            assert view == "season"

    def test_all_weeks_have_primary_style(self):
        """All regular season weeks should have 'primary' style."""
        for week in range(1, 19):
            stage_type = StageType.get_regular_season_week(week)
            style = get_button_style(stage_type)
            assert style == "primary"


class TestPlayoffMapping:
    """Tests for playoff stage mappings."""

    @pytest.mark.parametrize("stage_type,expected_text", [
        (StageType.WILD_CARD, "View Wild Card ▶"),
        (StageType.DIVISIONAL, "View Divisional ▶"),
        (StageType.CONFERENCE_CHAMPIONSHIP, "View Conference Finals ▶"),
        (StageType.SUPER_BOWL, "View Super Bowl ▶"),
    ])
    def test_playoff_button_text(self, stage_type, expected_text):
        """Playoff stages should have correct button text."""
        text = get_button_text(stage_type)
        assert text == expected_text

    def test_all_playoff_stages_target_playoffs_view(self):
        """All playoff stages should target 'playoffs' view."""
        playoff_stages = [
            StageType.WILD_CARD,
            StageType.DIVISIONAL,
            StageType.CONFERENCE_CHAMPIONSHIP,
            StageType.SUPER_BOWL,
        ]
        for stage_type in playoff_stages:
            view = get_target_view(stage_type)
            assert view == "playoffs"

    def test_all_playoff_stages_have_urgent_style(self):
        """All playoff stages should have 'urgent' style."""
        playoff_stages = [
            StageType.WILD_CARD,
            StageType.DIVISIONAL,
            StageType.CONFERENCE_CHAMPIONSHIP,
            StageType.SUPER_BOWL,
        ]
        for stage_type in playoff_stages:
            style = get_button_style(stage_type)
            assert style == "urgent"


class TestOffseasonMapping:
    """Tests for offseason stage mappings."""

    @pytest.mark.parametrize("stage_type,expected_text", [
        (StageType.OFFSEASON_HONORS, "Awards ▶"),
        (StageType.OFFSEASON_FRANCHISE_TAG, "Franchise Tag ▶"),
        (StageType.OFFSEASON_RESIGNING, "Re-signing ▶"),
        (StageType.OFFSEASON_FREE_AGENCY, "Free Agency ▶"),
        (StageType.OFFSEASON_TRADING, "Trading ▶"),
        (StageType.OFFSEASON_DRAFT, "Draft ▶"),
        (StageType.OFFSEASON_TRAINING_CAMP, "Training Camp ▶"),
        (StageType.OFFSEASON_WAIVER_WIRE, "Waiver Wire ▶"),
        (StageType.OFFSEASON_OWNER, "Review Proposals ▶"),
    ])
    def test_offseason_button_text(self, stage_type, expected_text):
        """Offseason stages should have correct button text."""
        text = get_button_text(stage_type)
        assert text == expected_text

    def test_honors_targets_season_recap(self):
        """Honors stage should target season_recap view."""
        view = get_target_view(StageType.OFFSEASON_HONORS)
        assert view == "season_recap"

    def test_other_offseason_stages_target_owner_view(self):
        """Most offseason stages should target owner view."""
        offseason_stages = [
            StageType.OFFSEASON_FRANCHISE_TAG,
            StageType.OFFSEASON_RESIGNING,
            StageType.OFFSEASON_FREE_AGENCY,
            StageType.OFFSEASON_TRADING,
            StageType.OFFSEASON_DRAFT,
            StageType.OFFSEASON_TRAINING_CAMP,
            StageType.OFFSEASON_WAIVER_WIRE,
            StageType.OFFSEASON_OWNER,
        ]
        for stage_type in offseason_stages:
            view = get_target_view(stage_type)
            assert view == "owner"

    def test_draft_has_urgent_style(self):
        """Draft stage should have urgent style."""
        style = get_button_style(StageType.OFFSEASON_DRAFT)
        assert style == "urgent"

    def test_owner_review_has_urgent_style(self):
        """Owner review stage should have urgent style."""
        style = get_button_style(StageType.OFFSEASON_OWNER)
        assert style == "urgent"

    def test_other_offseason_stages_have_action_style(self):
        """Most offseason stages should have action style."""
        action_stages = [
            StageType.OFFSEASON_HONORS,
            StageType.OFFSEASON_FRANCHISE_TAG,
            StageType.OFFSEASON_RESIGNING,
            StageType.OFFSEASON_FREE_AGENCY,
            StageType.OFFSEASON_TRADING,
            StageType.OFFSEASON_TRAINING_CAMP,
            StageType.OFFSEASON_WAIVER_WIRE,
        ]
        for stage_type in action_stages:
            style = get_button_style(stage_type)
            assert style == "action"


class TestPreseasonMapping:
    """Tests for preseason stage mappings."""

    @pytest.mark.parametrize("stage_type", [
        StageType.OFFSEASON_PRESEASON_W1,
        StageType.OFFSEASON_PRESEASON_W2,
        StageType.OFFSEASON_PRESEASON_W3,
    ])
    def test_preseason_stages_have_mappings(self, stage_type):
        """All preseason stages should have action mappings."""
        # Note: Preseason stages are not in the current STAGE_ACTIONS mapping
        # They will fall through to the default mapping
        action = get_action_for_stage(stage_type)
        assert action is not None
        assert "text" in action
        assert "target_view" in action


class TestCoverageValidation:
    """Validate that all StageType entries have action mappings."""

    def test_all_active_stage_types_have_action_mappings(self):
        """Ensure all active StageType entries have explicit action mappings."""
        all_stages = set(StageType)
        covered_stages = set(STAGE_ACTIONS.keys())
        missing_stages = all_stages - covered_stages

        # Document stages that intentionally use defaults
        # Deprecated preseason stages and new preseason stages use defaults
        allowed_missing = {
            StageType.PRESEASON_WEEK_1,  # DEPRECATED
            StageType.PRESEASON_WEEK_2,  # DEPRECATED
            StageType.PRESEASON_WEEK_3,  # DEPRECATED
            StageType.OFFSEASON_PRESEASON_W1,  # Uses default
            StageType.OFFSEASON_PRESEASON_W2,  # Uses default
            StageType.OFFSEASON_PRESEASON_W3,  # Uses default
        }

        unexpected_missing = missing_stages - allowed_missing

        assert not unexpected_missing, (
            f"Missing action mappings for stages: {unexpected_missing}\n"
            f"Add entries to STAGE_ACTIONS or document in allowed_missing."
        )

    def test_all_mappings_have_required_keys(self):
        """All action mappings should have required keys."""
        required_keys = {"text", "target_view", "category", "style"}

        for stage_type, action in STAGE_ACTIONS.items():
            missing_keys = required_keys - set(action.keys())
            assert not missing_keys, (
                f"Stage {stage_type.name} missing required keys: {missing_keys}"
            )

    def test_all_mappings_have_valid_styles(self):
        """All action mappings should use valid style values."""
        valid_styles = {"primary", "urgent", "action"}

        for stage_type, action in STAGE_ACTIONS.items():
            style = action["style"]
            assert style in valid_styles, (
                f"Stage {stage_type.name} has invalid style '{style}'. "
                f"Must be one of {valid_styles}"
            )

    def test_all_playoff_stages_covered(self):
        """Verify all playoff stages are explicitly mapped."""
        playoff_stages = {
            StageType.WILD_CARD,
            StageType.DIVISIONAL,
            StageType.CONFERENCE_CHAMPIONSHIP,
            StageType.SUPER_BOWL,
        }
        covered = set(STAGE_ACTIONS.keys()) & playoff_stages
        assert covered == playoff_stages, (
            f"Missing playoff stage mappings: {playoff_stages - covered}"
        )

    def test_all_offseason_stages_covered(self):
        """Verify all active offseason stages are explicitly mapped."""
        from game_cycle.stage_definitions import OFFSEASON_STAGES

        # Exclude preseason stages (they use defaults)
        active_offseason = {
            s for s in OFFSEASON_STAGES
            if not s.name.startswith("OFFSEASON_PRESEASON_")
        }

        covered = set(STAGE_ACTIONS.keys()) & active_offseason
        assert covered == active_offseason, (
            f"Missing offseason stage mappings: {active_offseason - covered}"
        )


class TestDefaultMapping:
    """Tests for default fallback mapping."""

    def test_unmapped_stage_returns_default(self):
        """Unmapped stages should return default action."""
        # Use deprecated preseason stage as example
        action = get_action_for_stage(StageType.PRESEASON_WEEK_1)

        assert action["text"] == "Continue ▶"
        assert action["target_view"] == "season"
        assert action["category"] == "Game Day"
        assert action["style"] == "primary"

    def test_get_badge_returns_none_for_default(self):
        """Default mapping should return None for badge."""
        # Use deprecated preseason stage as example
        badge = get_badge_for_stage(StageType.PRESEASON_WEEK_1)
        assert badge is None
