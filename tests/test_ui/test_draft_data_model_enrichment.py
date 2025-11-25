"""
Tests for DraftDataModel enrichment methods.

These tests verify that draft picks are correctly enriched with:
1. Team data (name, abbreviation, colors)
2. Player data (for executed picks)
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add src to path
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add ui to path
ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ui')
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)


@pytest.fixture
def mock_team():
    """Create a mock Team object"""
    team = Mock()
    team.team_id = 4
    team.full_name = "Detroit Lions"
    team.abbreviation = "DET"
    team.colors = {
        'primary': '#0076B6',
        'secondary': '#B0B7BC'
    }
    return team


@pytest.fixture
def mock_team_loader(mock_team):
    """Create a mock TeamDataLoader"""
    loader = Mock()
    loader.get_team_by_id.return_value = mock_team
    return loader


@pytest.fixture
def mock_draft_class_api():
    """Create a mock DraftClassAPI"""
    api = Mock()

    # Mock prospect data
    prospect = {
        'player_id': 1001,
        'first_name': 'John',
        'last_name': 'Smith',
        'position': 'QB',
        'college': 'Michigan',
        'overall': 92
    }

    api.get_prospect_by_id.return_value = prospect
    return api


@pytest.fixture
def draft_data_model(mock_team_loader, mock_draft_class_api):
    """Create DraftDataModel with mocked dependencies"""
    from domain_models.draft_data_model import DraftDataModel

    model = DraftDataModel(
        db_path=':memory:',
        dynasty_id='test_dynasty',
        season=2025
    )

    # Replace with mocks
    model.team_loader = mock_team_loader
    model.draft_class_api = mock_draft_class_api

    return model


class TestEnrichPicksWithTeamData:
    """Test _enrich_picks_with_team_data() method"""

    def test_adds_team_name(self, draft_data_model, mock_team):
        """Test that team name is added to pick"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'original_team_id': 4,
            }
        ]

        enriched = draft_data_model._enrich_picks_with_team_data(picks)

        assert enriched[0]['team_name'] == 'Detroit Lions'

    def test_adds_team_abbreviation(self, draft_data_model, mock_team):
        """Test that team abbreviation is added"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'original_team_id': 4,
            }
        ]

        enriched = draft_data_model._enrich_picks_with_team_data(picks)

        assert enriched[0]['team_abbrev'] == 'DET'

    def test_adds_team_colors(self, draft_data_model, mock_team):
        """Test that team colors are added"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'original_team_id': 4,
            }
        ]

        enriched = draft_data_model._enrich_picks_with_team_data(picks)

        assert enriched[0]['primary_color'] == '#0076B6'
        assert enriched[0]['secondary_color'] == '#B0B7BC'

    def test_adds_original_team_data(self, draft_data_model, mock_team):
        """Test that original team data is added (for traded picks)"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'original_team_id': 4,
            }
        ]

        enriched = draft_data_model._enrich_picks_with_team_data(picks)

        assert enriched[0]['original_team_name'] == 'Detroit Lions'
        assert enriched[0]['original_team_abbrev'] == 'DET'

    def test_handles_missing_team(self, draft_data_model):
        """Test graceful handling when team not found"""
        draft_data_model.team_loader.get_team_by_id.return_value = None

        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 999,
                'original_team_id': 999,
            }
        ]

        # Should not crash
        enriched = draft_data_model._enrich_picks_with_team_data(picks)

        # Should have placeholder values
        assert enriched[0]['team_name'] == 'Unknown Team'
        assert enriched[0]['team_abbrev'] == 'UNK'

    def test_enriches_multiple_picks(self, draft_data_model, mock_team):
        """Test enriching multiple picks"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'original_team_id': 4,
            },
            {
                'round_number': 1,
                'pick_in_round': 2,
                'overall_pick': 2,
                'team_id': 4,
                'original_team_id': 4,
            }
        ]

        enriched = draft_data_model._enrich_picks_with_team_data(picks)

        assert len(enriched) == 2
        assert all(p['team_name'] == 'Detroit Lions' for p in enriched)


class TestAddPlayerData:
    """Test _add_player_data() method"""

    def test_adds_player_data_for_executed_picks(self, draft_data_model, mock_draft_class_api):
        """Test that player data is added for executed picks"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'is_executed': True,
                'player_id': 1001
            }
        ]

        enriched = draft_data_model._add_player_data(picks)

        assert enriched[0]['player_name'] == 'John Smith'
        assert enriched[0]['position'] == 'QB'
        assert enriched[0]['college'] == 'Michigan'

    def test_adds_none_for_non_executed_picks(self, draft_data_model):
        """Test that None values are added for non-executed picks"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'is_executed': False,
            }
        ]

        enriched = draft_data_model._add_player_data(picks)

        assert enriched[0]['player_name'] is None
        assert enriched[0]['position'] is None
        assert enriched[0]['college'] is None

    def test_handles_missing_player_data(self, draft_data_model, mock_draft_class_api):
        """Test graceful handling when player not found"""
        mock_draft_class_api.get_prospect_by_id.return_value = None

        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'is_executed': True,
                'player_id': 9999
            }
        ]

        # Should not crash
        enriched = draft_data_model._add_player_data(picks)

        # Should have None values
        assert enriched[0]['player_name'] is None
        assert enriched[0]['position'] is None
        assert enriched[0]['college'] is None

    def test_handles_mixed_executed_and_non_executed(self, draft_data_model, mock_draft_class_api):
        """Test handling mix of executed and non-executed picks"""
        picks = [
            {
                'round_number': 1,
                'pick_in_round': 1,
                'overall_pick': 1,
                'team_id': 4,
                'is_executed': True,
                'player_id': 1001
            },
            {
                'round_number': 1,
                'pick_in_round': 2,
                'overall_pick': 2,
                'team_id': 5,
                'is_executed': False,
            }
        ]

        enriched = draft_data_model._add_player_data(picks)

        # First pick should have player data
        assert enriched[0]['player_name'] == 'John Smith'

        # Second pick should have None
        assert enriched[1]['player_name'] is None


class TestFullEnrichmentFlow:
    """Test complete enrichment flow in get_draft_order()"""

    def test_complete_enrichment(self, draft_data_model, mock_team, mock_draft_class_api):
        """Test that picks are fully enriched with team and player data"""
        # This test would require mocking get_draft_order() to return base picks
        # Then verify enrichment is applied
        # For now, we'll test the individual methods above
        pass
