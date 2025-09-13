"""
Phase 1 Tests: Data Layer for NFL Schedule Generator

Tests the minimal YAGNI implementation:
- TeamDataManager
- StandingsProvider
- RivalryDetector
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from scheduling.data.team_data import TeamDataManager, Team
from scheduling.data.standings import StandingsProvider, TeamStanding
from scheduling.data.rivalries import RivalryDetector


class TestTeamDataManager:
    """Test minimal team data loading"""
    
    def test_manager_creation(self):
        """Test manager initializes successfully"""
        manager = TeamDataManager()
        assert len(manager) == 32
        assert len(manager.teams) == 32
    
    def test_team_loading(self):
        """Test teams are loaded correctly"""
        manager = TeamDataManager()
        
        # Test specific teams
        lions = manager.get_team(22)
        assert lions is not None
        assert lions.city == "Detroit"
        assert lions.nickname == "Lions"
        assert lions.abbreviation == "DET"
        assert lions.full_name == "Detroit Lions"
    
    def test_all_teams_exist(self):
        """Test all 32 NFL teams are loaded"""
        manager = TeamDataManager()
        
        for team_id in range(1, 33):
            team = manager.get_team(team_id)
            assert team is not None
            assert team.team_id == team_id
            assert manager.team_exists(team_id)
    
    def test_division_lookup(self):
        """Test division lookups work"""
        manager = TeamDataManager()
        
        # Test team has division
        lions = manager.get_team(22)
        division = lions.division
        assert division is not None
        
        # Test division opponents
        opponents = lions.division_opponents
        assert len(opponents) == 3  # 3 other teams in division
        assert 22 not in opponents  # Lions not in their own opponents
    
    def test_invalid_team_id(self):
        """Test invalid team ID handling"""
        manager = TeamDataManager()
        
        assert manager.get_team(0) is None
        assert manager.get_team(33) is None
        assert not manager.team_exists(0)
        assert not manager.team_exists(33)


class TestStandingsProvider:
    """Test minimal standings functionality"""
    
    def test_provider_creation(self):
        """Test provider initializes with default standings"""
        provider = StandingsProvider()
        assert len(provider.standings) == 32
    
    def test_division_places(self):
        """Test teams have valid division places"""
        provider = StandingsProvider()
        
        # Check all teams have valid places (1-4)
        for team_id in range(1, 33):
            place = provider.get_division_place(team_id)
            assert 1 <= place <= 4
    
    def test_standing_data(self):
        """Test standing data is reasonable"""
        provider = StandingsProvider()
        
        # Check a few teams have reasonable records
        for team_id in [1, 10, 20, 30]:
            standing = provider.get_standing(team_id)
            assert standing is not None
            assert standing.wins + standing.losses <= 17  # Max 17 games
            assert standing.wins >= 0
            assert standing.losses >= 0
            assert 0.0 <= standing.win_percentage <= 1.0
    
    def test_division_place_distribution(self):
        """Test each division has exactly one team per place"""
        provider = StandingsProvider()
        
        # Define division team IDs
        divisions = [
            [1, 2, 3, 4],      # AFC East
            [5, 6, 7, 8],      # AFC North
            [9, 10, 11, 12],   # AFC South
            [13, 14, 15, 16],  # AFC West
            [17, 18, 19, 20],  # NFC East
            [21, 22, 23, 24],  # NFC North
            [25, 26, 27, 28],  # NFC South
            [29, 30, 31, 32],  # NFC West
        ]
        
        for division in divisions:
            # Each division should have exactly one team in each place (1-4)
            for place in range(1, 5):
                teams_in_place = provider.get_teams_by_place(division, place)
                assert len(teams_in_place) == 1


class TestRivalryDetector:
    """Test minimal rivalry detection"""
    
    def test_detector_creation(self):
        """Test detector initializes successfully"""
        detector = RivalryDetector()
        assert detector.nfl_structure is not None
    
    def test_division_rivalries(self):
        """Test division rivalry detection"""
        detector = RivalryDetector()
        
        # Lions vs Packers (both NFC North)
        assert detector.are_division_rivals(22, 23)  # DET vs GB
        assert detector.are_rivals(22, 23)  # Should be same as division rivals
        
        # Lions vs Cowboys (different divisions)
        assert not detector.are_division_rivals(22, 17)  # DET vs DAL
        assert not detector.are_rivals(22, 17)
    
    def test_division_rival_lists(self):
        """Test getting division rival lists"""
        detector = RivalryDetector()
        
        # Lions should have 3 division rivals
        lions_rivals = detector.get_division_rivals(22)
        assert len(lions_rivals) == 3
        assert 22 not in lions_rivals  # Lions not rival to themselves
        
        # Should be same as get_rivals (YAGNI - only division rivals)
        all_rivals = detector.get_rivals(22)
        assert lions_rivals == all_rivals
    
    def test_team_not_rival_to_self(self):
        """Test team is not rival to itself"""
        detector = RivalryDetector()
        
        for team_id in [1, 10, 22, 32]:
            assert not detector.are_rivals(team_id, team_id)
    
    def test_rivalry_game_detection(self):
        """Test finding rivalry games in a team list"""
        detector = RivalryDetector()
        
        # NFC North teams
        nfc_north = [21, 22, 23, 24]  # CHI, DET, GB, MIN
        rivalry_games = detector.get_rivalry_games(nfc_north)
        
        # Should be 6 rivalry games (4 choose 2)
        assert len(rivalry_games) == 6
        
        # All should be actual rivals
        for team1, team2 in rivalry_games:
            assert detector.are_rivals(team1, team2)


class TestPhase1Integration:
    """Integration tests for Phase 1 components"""
    
    def test_full_phase1_integration(self):
        """Test all Phase 1 components work together"""
        # Initialize all components
        team_manager = TeamDataManager()
        standings = StandingsProvider()
        rivalries = RivalryDetector()
        
        # Test workflow: Get a team, check standing, find rivals
        lions = team_manager.get_team(22)
        assert lions is not None
        
        lions_place = standings.get_division_place(22)
        assert 1 <= lions_place <= 4
        
        lions_rivals = rivalries.get_rivals(22)
        assert len(lions_rivals) == 3
        
        # All rivals should be valid teams
        for rival_id in lions_rivals:
            rival_team = team_manager.get_team(rival_id)
            assert rival_team is not None
    
    def test_data_consistency(self):
        """Test data is consistent between components"""
        team_manager = TeamDataManager()
        rivalries = RivalryDetector()
        
        # Test that rivalry detection matches team manager's division data
        for team_id in [1, 10, 22, 32]:
            team = team_manager.get_team(team_id)
            team_rivals = rivalries.get_rivals(team_id)
            manager_rivals = team.division_opponents
            
            # Should be the same rivals
            assert set(team_rivals) == set(manager_rivals)


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])