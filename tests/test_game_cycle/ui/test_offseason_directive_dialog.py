"""
Tests for OffseasonDirectiveDialog.

Part of Milestone 13: Owner Review - Tollgate 1.
Tests UI behavior for the offseason directive dialog.

NOTE: These tests require running with PYTHONPATH=src or as part of
the full test suite. Run with: python -m pytest tests/ to ensure proper imports.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Ensure src is at the FRONT of path BEFORE importing (required for player_generation.archetypes)
_src_path = str(Path(__file__).parent.parent.parent.parent / "src")
_project_root = str(Path(__file__).parent.parent.parent.parent)

# Remove and re-add to ensure src is first
for path in [_src_path, _project_root]:
    while path in sys.path:
        sys.path.remove(path)
# Insert src first, then project_root
sys.path.insert(0, _project_root)
sys.path.insert(0, _src_path)

# Check if we can import the required modules
# If not, skip all tests in this module
try:
    from game_cycle_ui.dialogs.offseason_directive_dialog import OffseasonDirectiveDialog
    from game_cycle.models.owner_directives import OwnerDirectives
    from PySide6.QtWidgets import QApplication, QCheckBox
    from PySide6.QtCore import Qt
    HAS_IMPORTS = True
except ImportError as e:
    HAS_IMPORTS = False
    IMPORT_ERROR = str(e)

pytestmark = pytest.mark.skipif(
    not HAS_IMPORTS,
    reason=f"UI dialog tests require PYTHONPATH=src. Run: python -m pytest tests/"
)


def get_dialog_class():
    """Get dialog class."""
    return OffseasonDirectiveDialog


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_roster():
    """Sample roster for testing."""
    return [
        {"player_id": 1, "name": "Tom Brady", "position": "QB", "overall": 95},
        {"player_id": 2, "name": "Aaron Donald", "position": "DT", "overall": 99},
        {"player_id": 3, "name": "Davante Adams", "position": "WR", "overall": 92},
        {"player_id": 4, "name": "Tyreek Hill", "position": "WR", "overall": 91},
        {"player_id": 5, "name": "Jalen Ramsey", "position": "CB", "overall": 90},
        {"player_id": 6, "name": "Micah Parsons", "position": "LB", "overall": 89},
    ]


@pytest.fixture
def dialog(qapp, sample_roster):
    """Create OffseasonDirectiveDialog with sample roster."""
    OffseasonDirectiveDialog = get_dialog_class()
    dlg = OffseasonDirectiveDialog(
        dynasty_id="test-dynasty",
        team_id=1,
        season=2025,
        roster=sample_roster
    )
    yield dlg
    dlg.close()
    dlg.deleteLater()


# ============================================================================
# DIALOG INITIALIZATION TESTS
# ============================================================================

class TestOffseasonDirectiveDialogCreation:
    """Tests for dialog creation and initialization."""

    def test_creates_dialog(self, dialog):
        """Dialog initializes without error."""
        assert dialog is not None

    def test_stores_constructor_params(self, dialog):
        """Dialog stores constructor parameters."""
        assert dialog.dynasty_id == "test-dynasty"
        assert dialog.team_id == 1
        assert dialog.season == 2025
        assert len(dialog.roster) == 6

    def test_has_required_ui_widgets(self, dialog):
        """Dialog has all required UI widgets."""
        assert dialog.philosophy_group is not None
        assert dialog.budget_group is not None
        assert len(dialog.priority_combos) == 5
        assert dialog.protected_table is not None
        assert dialog.expendable_table is not None
        assert dialog.notes_edit is not None
        assert dialog.trust_gm_checkbox is not None
        assert dialog.preview_label is not None


# ============================================================================
# DEFAULT VALUE TESTS
# ============================================================================

class TestOffseasonDirectiveDialogDefaults:
    """Tests for default values."""

    def test_philosophy_defaults_to_maintain(self, dialog):
        """Default philosophy is 'maintain'."""
        value = dialog._get_selected_radio_value(dialog.philosophy_group)
        assert value == "maintain"

    def test_budget_defaults_to_moderate(self, dialog):
        """Default budget is 'moderate'."""
        value = dialog._get_selected_radio_value(dialog.budget_group)
        assert value == "moderate"

    def test_priority_combos_default_empty(self, dialog):
        """All priority combos default to empty."""
        for combo in dialog.priority_combos:
            assert combo.currentText() == ""

    def test_trust_gm_default_unchecked(self, dialog):
        """Trust GM checkbox defaults to unchecked."""
        assert not dialog.trust_gm_checkbox.isChecked()

    def test_notes_default_empty(self, dialog):
        """Notes text area defaults to empty."""
        assert dialog.notes_edit.toPlainText() == ""


# ============================================================================
# PLAYER TABLE TESTS
# ============================================================================

class TestOffseasonDirectiveDialogPlayerTables:
    """Tests for player selection tables."""

    def test_protected_table_populated(self, dialog, sample_roster):
        """Protected table has correct number of rows."""
        assert dialog.protected_table.rowCount() == len(sample_roster)

    def test_expendable_table_populated(self, dialog, sample_roster):
        """Expendable table has correct number of rows."""
        assert dialog.expendable_table.rowCount() == len(sample_roster)

    def test_table_sorted_by_overall(self, dialog):
        """Tables are sorted by overall rating descending."""
        # First row should be highest overall (99 - Aaron Donald)
        first_row_ovr = dialog.protected_table.item(0, 3).text()
        assert first_row_ovr == "99"

    def test_get_selected_player_ids_empty(self, dialog):
        """No players selected initially."""
        protected = dialog._get_selected_player_ids(dialog.protected_table)
        expendable = dialog._get_selected_player_ids(dialog.expendable_table)
        assert protected == []
        assert expendable == []

    def test_protected_count_label_updates(self, dialog):
        """Protected count label updates when player selected."""
        # Select first player
        checkbox_widget = dialog.protected_table.cellWidget(0, 0)
        checkbox = checkbox_widget.findChild(QCheckBox)
        checkbox.setChecked(True)

        assert "1/5" in dialog.protected_count.text()

    def test_expendable_count_label_updates(self, dialog):
        """Expendable count label updates when player selected."""
        # Select first player
        checkbox_widget = dialog.expendable_table.cellWidget(0, 0)
        checkbox = checkbox_widget.findChild(QCheckBox)
        checkbox.setChecked(True)

        assert "1/10" in dialog.expendable_count.text()


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestOffseasonDirectiveDialogValidation:
    """Tests for dialog validation."""

    def test_validates_protected_max(self, dialog):
        """Validates max 5 protected players."""
        # Select 6 players in protected table
        for row in range(6):
            checkbox_widget = dialog.protected_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            checkbox.setChecked(True)

        valid, error = dialog._validate()
        assert valid is False
        assert "5" in error

    def test_validates_expendable_max(self, qapp, sample_roster):
        """Validates max 10 expendable players."""
        OffseasonDirectiveDialog = get_dialog_class()
        # Create dialog with more players to test limit
        large_roster = [
            {"player_id": i, "name": f"Player {i}", "position": "QB", "overall": 80}
            for i in range(12)
        ]
        dlg = OffseasonDirectiveDialog(
            dynasty_id="test",
            team_id=1,
            season=2025,
            roster=large_roster
        )

        # Select 11 players
        for row in range(11):
            checkbox_widget = dlg.expendable_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            checkbox.setChecked(True)

        valid, error = dlg._validate()
        assert valid is False
        assert "10" in error

        dlg.close()
        dlg.deleteLater()

    def test_validates_no_overlap(self, dialog):
        """Validates no overlap between protected and expendable."""
        # Select same player (row 0) in both tables
        protected_checkbox = dialog.protected_table.cellWidget(0, 0).findChild(QCheckBox)
        expendable_checkbox = dialog.expendable_table.cellWidget(0, 0).findChild(QCheckBox)

        protected_checkbox.setChecked(True)
        expendable_checkbox.setChecked(True)

        valid, error = dialog._validate()
        assert valid is False
        assert "protected and expendable" in error.lower()

    def test_valid_selection_passes(self, dialog):
        """Valid selection passes validation."""
        # Select 3 protected, 5 expendable, no overlap
        for row in range(3):
            checkbox_widget = dialog.protected_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            checkbox.setChecked(True)

        for row in range(3, 6):
            checkbox_widget = dialog.expendable_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            checkbox.setChecked(True)

        valid, error = dialog._validate()
        assert valid is True
        assert error == ""


# ============================================================================
# EXISTING DIRECTIVES LOADING TESTS
# ============================================================================

class TestOffseasonDirectiveDialogLoading:
    """Tests for loading existing directives."""

    def test_loads_existing_directives(self, qapp, sample_roster):
        """Loads existing directives into form."""
        OffseasonDirectiveDialog = get_dialog_class()
        existing = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            team_philosophy="win_now",
            budget_stance="aggressive",
            protected_player_ids=[1],
            expendable_player_ids=[2, 3],
            owner_notes="My notes",
            trust_gm=True
        )

        dlg = OffseasonDirectiveDialog(
            dynasty_id="test",
            team_id=1,
            season=2025,
            roster=sample_roster,
            existing_directives=existing
        )

        assert dlg._get_selected_radio_value(dlg.philosophy_group) == "win_now"
        assert dlg._get_selected_radio_value(dlg.budget_group) == "aggressive"
        assert dlg.notes_edit.toPlainText() == "My notes"
        assert dlg.trust_gm_checkbox.isChecked()

        dlg.close()
        dlg.deleteLater()

    def test_loads_priority_positions(self, qapp, sample_roster):
        """Loads priority positions into combos."""
        OffseasonDirectiveDialog = get_dialog_class()
        existing = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=["QB", "WR", "CB"]
        )

        dlg = OffseasonDirectiveDialog(
            dynasty_id="test",
            team_id=1,
            season=2025,
            roster=sample_roster,
            existing_directives=existing
        )

        assert dlg.priority_combos[0].currentText() == "QB"
        assert dlg.priority_combos[1].currentText() == "WR"
        assert dlg.priority_combos[2].currentText() == "CB"

        dlg.close()
        dlg.deleteLater()


# ============================================================================
# SIGNAL EMISSION TESTS
# ============================================================================

class TestOffseasonDirectiveDialogSignals:
    """Tests for signal emission."""

    def test_skip_emits_default_directives(self, dialog):
        """Skip button emits default directives."""
        emitted = []
        dialog.directive_saved.connect(lambda d: emitted.append(d))

        dialog._on_skip()

        assert len(emitted) == 1
        assert emitted[0].team_philosophy == "maintain"
        assert emitted[0].budget_stance == "moderate"
        assert emitted[0].trust_gm is False

    def test_save_emits_directives(self, dialog):
        """Save button emits directives with form values."""
        emitted = []
        dialog.directive_saved.connect(lambda d: emitted.append(d))

        # Set some values
        for btn in dialog.philosophy_group.buttons():
            if btn.property("value") == "rebuild":
                btn.setChecked(True)
                break

        dialog.trust_gm_checkbox.setChecked(True)
        dialog.notes_edit.setPlainText("Test notes")

        dialog._on_save()

        assert len(emitted) == 1
        assert emitted[0].team_philosophy == "rebuild"
        assert emitted[0].trust_gm is True
        assert emitted[0].owner_notes == "Test notes"


# ============================================================================
# PREVIEW TESTS
# ============================================================================

class TestOffseasonDirectiveDialogPreview:
    """Tests for preview section."""

    def test_preview_updates_on_philosophy_change(self, dialog):
        """Preview updates when philosophy changes."""
        # Change to win_now and trigger update
        for btn in dialog.philosophy_group.buttons():
            if btn.property("value") == "win_now":
                btn.setChecked(True)
                dialog._update_preview()  # Manually trigger update
                break

        assert "Win Now" in dialog.preview_label.text()

    def test_preview_shows_trust_gm_status(self, dialog):
        """Preview shows trust GM status."""
        assert "No" in dialog.preview_label.text()

        dialog.trust_gm_checkbox.setChecked(True)
        dialog._update_preview()

        assert "Yes" in dialog.preview_label.text()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
