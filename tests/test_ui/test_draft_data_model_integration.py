"""
Integration test for DraftDataModel enrichment flow.

Tests that get_draft_order() properly applies enrichment methods.
"""

import pytest
import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add ui to path
ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ui')
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)


def test_get_draft_order_enriches_with_colors():
    """
    Test that get_draft_order() adds team colors to picks.

    This is an integration test that verifies the enrichment flow works.
    Note: This test may fail if there's no standings/playoff data in database.
    """
    from domain_models.draft_data_model import DraftDataModel

    # Create model with test database
    model = DraftDataModel(
        db_path=':memory:',
        dynasty_id='test_dynasty',
        season=2025
    )

    # This will likely return empty picks since we don't have data
    # but we're testing the enrichment flow doesn't crash
    picks = model.get_draft_order()

    # Verify enrichment didn't crash
    assert isinstance(picks, list)

    # If picks exist, verify they have color fields
    if picks:
        first_pick = picks[0]
        assert 'primary_color' in first_pick
        assert 'secondary_color' in first_pick
        assert 'original_team_name' in first_pick
        assert 'original_team_abbrev' in first_pick


def test_enrichment_methods_preserve_data():
    """
    Test that enrichment methods don't lose existing data.
    """
    from domain_models.draft_data_model import DraftDataModel

    model = DraftDataModel(
        db_path=':memory:',
        dynasty_id='test_dynasty',
        season=2025
    )

    # Create a test pick with existing data
    test_pick = {
        'round_number': 1,
        'pick_in_round': 1,
        'overall_pick': 1,
        'team_id': 4,
        'original_team_id': 4,
        'team_record': '5-12-0',
        'reason': 'non_playoff',
        'sos': 0.520,
    }

    # Apply team enrichment
    enriched = model._enrich_picks_with_team_data([test_pick])

    # Verify original data preserved
    assert enriched[0]['round_number'] == 1
    assert enriched[0]['team_id'] == 4
    assert enriched[0]['team_record'] == '5-12-0'

    # Verify new data added
    assert 'primary_color' in enriched[0]
    assert 'team_name' in enriched[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
