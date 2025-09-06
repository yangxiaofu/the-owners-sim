"""
Test Suite for Scoreboard System

Comprehensive tests for scoreboard functionality including score tracking,
scoring events, validation, and edge cases.
"""

import pytest
from src.game_management.scoreboard import Scoreboard, ScoringType, ScoringEvent
from src.constants.team_ids import TeamIDs


class TestScoringType:
    """Test ScoringType enum values"""
    
    def test_scoring_type_values(self):
        """Test that scoring types have correct point values"""
        assert ScoringType.TOUCHDOWN.value == 6
        assert ScoringType.FIELD_GOAL.value == 3
        assert ScoringType.SAFETY.value == 2
        assert ScoringType.EXTRA_POINT.value == 1
        assert ScoringType.TWO_POINT_CONVERSION.value == 2


class TestScoringEvent:
    """Test ScoringEvent data class"""
    
    def test_valid_scoring_event(self):
        """Test creating a valid scoring event"""
        event = ScoringEvent(
            team_id=TeamIDs.DETROIT_LIONS,
            scoring_type=ScoringType.TOUCHDOWN,
            points=6,
            description="25-yard rush by RB",
            quarter=2,
            game_time="8:45"
        )
        
        assert event.team_id == TeamIDs.DETROIT_LIONS
        assert event.scoring_type == ScoringType.TOUCHDOWN
        assert event.points == 6
        assert event.description == "25-yard rush by RB"
        assert event.quarter == 2
        assert event.game_time == "8:45"
    
    def test_scoring_event_defaults(self):
        """Test scoring event with default values"""
        event = ScoringEvent(
            team_id=TeamIDs.GREEN_BAY_PACKERS,
            scoring_type=ScoringType.FIELD_GOAL,
            points=3
        )
        
        assert event.description == ""
        assert event.quarter == 1
        assert event.game_time == ""
    
    def test_invalid_team_id(self):
        """Test scoring event with invalid team ID"""
        with pytest.raises(ValueError, match="Invalid team_id"):
            ScoringEvent(
                team_id=0,  # Invalid
                scoring_type=ScoringType.TOUCHDOWN,
                points=6
            )
        
        with pytest.raises(ValueError, match="Invalid team_id"):
            ScoringEvent(
                team_id=33,  # Invalid
                scoring_type=ScoringType.TOUCHDOWN,
                points=6
            )
    
    def test_invalid_quarter(self):
        """Test scoring event with invalid quarter"""
        with pytest.raises(ValueError, match="Invalid quarter"):
            ScoringEvent(
                team_id=TeamIDs.DETROIT_LIONS,
                scoring_type=ScoringType.TOUCHDOWN,
                points=6,
                quarter=0  # Invalid
            )
        
        with pytest.raises(ValueError, match="Invalid quarter"):
            ScoringEvent(
                team_id=TeamIDs.DETROIT_LIONS,
                scoring_type=ScoringType.TOUCHDOWN,
                points=6,
                quarter=5  # Invalid
            )
    
    def test_points_mismatch(self):
        """Test scoring event with mismatched points and scoring type"""
        with pytest.raises(ValueError, match="Points mismatch"):
            ScoringEvent(
                team_id=TeamIDs.DETROIT_LIONS,
                scoring_type=ScoringType.TOUCHDOWN,
                points=3  # Should be 6 for touchdown
            )


class TestScoreboard:
    """Test Scoreboard class functionality"""
    
    def test_scoreboard_initialization(self):
        """Test scoreboard initialization"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        assert scoreboard.home_team_id == TeamIDs.DETROIT_LIONS
        assert scoreboard.away_team_id == TeamIDs.GREEN_BAY_PACKERS
        assert scoreboard.get_score() == {TeamIDs.DETROIT_LIONS: 0, TeamIDs.GREEN_BAY_PACKERS: 0}
        assert scoreboard.get_scoring_history() == []
    
    def test_invalid_team_ids_initialization(self):
        """Test scoreboard with invalid team IDs"""
        # Invalid team ID
        with pytest.raises(ValueError, match="Invalid home_team_id"):
            Scoreboard(0, TeamIDs.GREEN_BAY_PACKERS)
        
        with pytest.raises(ValueError, match="Invalid away_team_id"):
            Scoreboard(TeamIDs.DETROIT_LIONS, 33)
        
        # Same team IDs
        with pytest.raises(ValueError, match="Home and away team IDs must be different"):
            Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.DETROIT_LIONS)
    
    def test_add_touchdown(self):
        """Test adding a touchdown"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        scoreboard.add_score(
            TeamIDs.DETROIT_LIONS,
            ScoringType.TOUCHDOWN,
            "25-yard rush",
            quarter=2
        )
        
        assert scoreboard.get_team_score(TeamIDs.DETROIT_LIONS) == 6
        assert scoreboard.get_team_score(TeamIDs.GREEN_BAY_PACKERS) == 0
        
        history = scoreboard.get_scoring_history()
        assert len(history) == 1
        assert history[0].team_id == TeamIDs.DETROIT_LIONS
        assert history[0].scoring_type == ScoringType.TOUCHDOWN
        assert history[0].points == 6
        assert history[0].description == "25-yard rush"
        assert history[0].quarter == 2
    
    def test_add_field_goal(self):
        """Test adding a field goal"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        scoreboard.add_score(
            TeamIDs.GREEN_BAY_PACKERS,
            ScoringType.FIELD_GOAL,
            "42-yard FG"
        )
        
        assert scoreboard.get_team_score(TeamIDs.DETROIT_LIONS) == 0
        assert scoreboard.get_team_score(TeamIDs.GREEN_BAY_PACKERS) == 3
    
    def test_add_safety(self):
        """Test adding a safety"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        scoreboard.add_score(
            TeamIDs.DETROIT_LIONS,
            ScoringType.SAFETY,
            "QB tackled in end zone"
        )
        
        assert scoreboard.get_team_score(TeamIDs.DETROIT_LIONS) == 2
    
    def test_multiple_scores(self):
        """Test multiple scoring events"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        # Lions touchdown
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.TOUCHDOWN, "TD pass")
        # Lions extra point
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.EXTRA_POINT, "PAT good")
        # Packers field goal
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.FIELD_GOAL, "35-yard FG")
        
        assert scoreboard.get_team_score(TeamIDs.DETROIT_LIONS) == 7
        assert scoreboard.get_team_score(TeamIDs.GREEN_BAY_PACKERS) == 3
        
        history = scoreboard.get_scoring_history()
        assert len(history) == 3
    
    def test_add_score_invalid_team(self):
        """Test adding score for team not in game"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        with pytest.raises(ValueError, match="Team .* is not in this game"):
            scoreboard.add_score(TeamIDs.CHICAGO_BEARS, ScoringType.TOUCHDOWN)
    
    def test_get_team_score_invalid_team(self):
        """Test getting score for team not in game"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        with pytest.raises(ValueError, match="Team .* is not in this game"):
            scoreboard.get_team_score(TeamIDs.CHICAGO_BEARS)
    
    def test_get_team_scoring_history(self):
        """Test getting scoring history for specific team"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.TOUCHDOWN)
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.FIELD_GOAL)
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.EXTRA_POINT)
        
        lions_history = scoreboard.get_team_scoring_history(TeamIDs.DETROIT_LIONS)
        assert len(lions_history) == 2
        assert all(event.team_id == TeamIDs.DETROIT_LIONS for event in lions_history)
        
        packers_history = scoreboard.get_team_scoring_history(TeamIDs.GREEN_BAY_PACKERS)
        assert len(packers_history) == 1
        assert packers_history[0].scoring_type == ScoringType.FIELD_GOAL
    
    def test_is_tied(self):
        """Test tie detection"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        # Initially tied at 0-0
        assert scoreboard.is_tied() is True
        
        # Lions score
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.FIELD_GOAL)
        assert scoreboard.is_tied() is False
        
        # Packers tie it up
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.FIELD_GOAL)
        assert scoreboard.is_tied() is True
    
    def test_get_leading_team(self):
        """Test leading team detection"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        # Initially tied
        assert scoreboard.get_leading_team() is None
        
        # Lions take the lead
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.TOUCHDOWN)
        assert scoreboard.get_leading_team() == TeamIDs.DETROIT_LIONS
        
        # Packers take the lead
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.TOUCHDOWN)
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.EXTRA_POINT)
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.FIELD_GOAL)  # 10 points
        assert scoreboard.get_leading_team() == TeamIDs.GREEN_BAY_PACKERS
    
    def test_get_score_difference(self):
        """Test score difference calculation"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        # Initially 0 difference
        assert scoreboard.get_score_difference() == 0
        
        # Lions 7, Packers 0
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.TOUCHDOWN)
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.EXTRA_POINT)
        assert scoreboard.get_score_difference() == 7
        
        # Lions 7, Packers 3
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.FIELD_GOAL)
        assert scoreboard.get_score_difference() == 4
    
    def test_reset_scores(self):
        """Test resetting scores"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        # Add some scores
        scoreboard.add_score(TeamIDs.DETROIT_LIONS, ScoringType.TOUCHDOWN)
        scoreboard.add_score(TeamIDs.GREEN_BAY_PACKERS, ScoringType.FIELD_GOAL)
        
        assert scoreboard.get_team_score(TeamIDs.DETROIT_LIONS) == 6
        assert len(scoreboard.get_scoring_history()) == 2
        
        # Reset
        scoreboard.reset_scores()
        
        assert scoreboard.get_team_score(TeamIDs.DETROIT_LIONS) == 0
        assert scoreboard.get_team_score(TeamIDs.GREEN_BAY_PACKERS) == 0
        assert len(scoreboard.get_scoring_history()) == 0
    
    def test_string_representations(self):
        """Test string representation methods"""
        scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
        
        # Test __str__
        str_repr = str(scoreboard)
        assert f"Team {TeamIDs.DETROIT_LIONS}: 0" in str_repr
        assert f"Team {TeamIDs.GREEN_BAY_PACKERS}: 0" in str_repr
        
        # Test __repr__
        repr_str = repr(scoreboard)
        assert "Scoreboard" in repr_str
        assert f"home_team={TeamIDs.DETROIT_LIONS}" in repr_str
        assert f"away_team={TeamIDs.GREEN_BAY_PACKERS}" in repr_str