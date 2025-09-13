"""
Unit tests for CentralizedStatsAggregator

Tests the statistics bridge between PlayResult objects and the existing
PlayerStatsAccumulator/TeamStatsAccumulator infrastructure.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Import classes under test
from src.game_management.centralized_stats_aggregator import (
    CentralizedStatsAggregator,
    GameLevelStats
)
from src.play_engine.core.play_result import PlayResult
from src.play_engine.simulation.stats import (
    PlayStatsSummary,
    PlayerStats,
    TeamStats
)
from src.play_engine.play_types.base_types import PlayType
from src.constants.team_ids import TeamIDs


class TestGameLevelStats:
    """Test the GameLevelStats data structure"""
    
    def test_initialization(self):
        """Test GameLevelStats initialization with default values"""
        game_stats = GameLevelStats(
            home_team_id=TeamIDs.DETROIT_LIONS,
            away_team_id=TeamIDs.SAN_FRANCISCO_49ERS
        )
        
        assert game_stats.home_team_id == TeamIDs.DETROIT_LIONS
        assert game_stats.away_team_id == TeamIDs.SAN_FRANCISCO_49ERS
        assert game_stats.total_plays_run == 0
        assert game_stats.touchdowns == 0
        assert game_stats.penalty_plays == 0
        assert game_stats.final_score == {}
        assert game_stats.winner_team_id is None
    
    def test_get_summary(self):
        """Test GameLevelStats summary generation"""
        game_stats = GameLevelStats(
            home_team_id=TeamIDs.DETROIT_LIONS,
            away_team_id=TeamIDs.SAN_FRANCISCO_49ERS
        )
        game_stats.total_plays_run = 120
        game_stats.touchdowns = 5
        game_stats.field_goals_made = 2
        game_stats.final_score = {TeamIDs.DETROIT_LIONS: 21, TeamIDs.SAN_FRANCISCO_49ERS: 17}
        game_stats.winner_team_id = TeamIDs.DETROIT_LIONS
        
        summary = game_stats.get_summary()
        
        assert summary["game_info"]["home_team_id"] == TeamIDs.DETROIT_LIONS
        assert summary["game_info"]["away_team_id"] == TeamIDs.SAN_FRANCISCO_49ERS
        assert summary["game_info"]["final_score"] == {TeamIDs.DETROIT_LIONS: 21, TeamIDs.SAN_FRANCISCO_49ERS: 17}
        assert summary["game_info"]["winner"] == TeamIDs.DETROIT_LIONS
        
        assert summary["play_stats"]["total_plays"] == 120
        assert summary["drive_outcomes"]["touchdowns"] == 5
        assert summary["drive_outcomes"]["field_goals_made"] == 2


class TestCentralizedStatsAggregator:
    """Test the main CentralizedStatsAggregator class"""
    
    @pytest.fixture
    def aggregator(self):
        """Create a CentralizedStatsAggregator for testing"""
        return CentralizedStatsAggregator(
            home_team_id=TeamIDs.DETROIT_LIONS,
            away_team_id=TeamIDs.SAN_FRANCISCO_49ERS,
            game_identifier="TestGame_Lions_vs_49ers"
        )
    
    def test_initialization(self, aggregator):
        """Test aggregator initialization"""
        assert aggregator.home_team_id == TeamIDs.DETROIT_LIONS
        assert aggregator.away_team_id == TeamIDs.SAN_FRANCISCO_49ERS
        assert aggregator.game_id == "TestGame_Lions_vs_49ers"
        
        # Check that existing components are initialized
        assert aggregator.player_stats is not None
        assert aggregator.team_stats is not None
        assert aggregator.game_stats is not None
        
        # Check initial state
        assert aggregator.get_plays_processed() == 0
        assert aggregator.get_drives_completed() == 0
        assert not aggregator.is_statistics_complete()
    
    def test_record_play_result_basic(self, aggregator):
        """Test basic play result recording without detailed stats"""
        play_result = PlayResult(
            outcome="rush",
            yards=5,
            points=0,
            time_elapsed=30.0,
            is_scoring_play=False,
            achieved_first_down=True,
            penalty_occurred=False
        )
        
        aggregator.record_play_result(
            play_result=play_result,
            possessing_team_id=TeamIDs.DETROIT_LIONS,
            down=1,
            yards_to_go=10,
            field_position=50
        )
        
        # Verify play tracking
        assert aggregator.get_plays_processed() == 1
        assert aggregator.is_statistics_complete()
        
        # Verify game-level stats
        assert aggregator.game_stats.total_plays_run == 1
        assert aggregator.game_stats.total_game_time_seconds == 30.0
        assert aggregator.game_stats.first_downs_total == 1  # achieved_first_down was True
        assert aggregator.game_stats.penalty_plays == 0
    
    def test_record_play_result_with_detailed_stats(self, aggregator):
        """Test play result recording with detailed player statistics"""
        # Create mock PlayStatsSummary with properly configured attributes
        mock_stats_summary = Mock(spec=PlayStatsSummary)
        mock_stats_summary.yards_gained = 8
        mock_stats_summary.time_elapsed = 25.0
        mock_stats_summary.penalty_occurred = False  # Important: avoid penalty processing in this test
        mock_stats_summary.penalty_instance = None
        mock_stats_summary.player_stats = [
            PlayerStats(player_name="Lions RB", player_number=32, position="RB", carries=1, rushing_yards=8),
            PlayerStats(player_name="Lions QB", player_number=9, position="QB")
        ]
        
        play_result = PlayResult(
            outcome="rush", 
            yards=8,
            points=0,
            time_elapsed=25.0,
            player_stats_summary=mock_stats_summary,
            achieved_first_down=True
        )
        
        aggregator.record_play_result(
            play_result=play_result,
            possessing_team_id=TeamIDs.DETROIT_LIONS,
            down=2,
            yards_to_go=7,
            field_position=45
        )
        
        # Verify the detailed stats were processed
        assert aggregator.get_plays_processed() == 1
        assert aggregator.game_stats.total_plays_run == 1
        assert aggregator.game_stats.first_downs_total == 1
    
    def test_record_scoring_plays(self, aggregator):
        """Test recording of various scoring plays"""
        # Touchdown
        td_result = PlayResult(
            outcome="rushing_touchdown",
            yards=15,
            points=6,
            time_elapsed=20.0,
            is_scoring_play=True
        )
        
        aggregator.record_play_result(
            play_result=td_result,
            possessing_team_id=TeamIDs.DETROIT_LIONS
        )
        
        # Field goal
        fg_result = PlayResult(
            outcome="field_goal_made",
            yards=0,
            points=3,
            time_elapsed=25.0,
            is_scoring_play=True
        )
        
        aggregator.record_play_result(
            play_result=fg_result,
            possessing_team_id=TeamIDs.DETROIT_LIONS
        )
        
        # Safety
        safety_result = PlayResult(
            outcome="safety",
            yards=0,
            points=2,
            time_elapsed=10.0,
            is_scoring_play=True
        )
        
        aggregator.record_play_result(
            play_result=safety_result,
            possessing_team_id=TeamIDs.SAN_FRANCISCO_49ERS  # Scored against Lions
        )
        
        # Verify scoring statistics
        assert aggregator.game_stats.scoring_plays == 3
        assert aggregator.game_stats.touchdowns == 1
        assert aggregator.game_stats.field_goals_made == 1
        assert aggregator.game_stats.safeties == 1
    
    def test_record_special_situations(self, aggregator):
        """Test recording of special situations like turnovers, penalties, big plays"""
        # Turnover
        turnover_result = PlayResult(
            outcome="interception",
            yards=0,
            time_elapsed=15.0,
            is_turnover=True,
            turnover_type="interception"
        )
        
        aggregator.record_play_result(
            play_result=turnover_result,
            possessing_team_id=TeamIDs.DETROIT_LIONS
        )
        
        # Penalty play
        penalty_result = PlayResult(
            outcome="rush",
            yards=3,
            time_elapsed=28.0,
            penalty_occurred=True,
            penalty_yards=5
        )
        
        aggregator.record_play_result(
            play_result=penalty_result,
            possessing_team_id=TeamIDs.DETROIT_LIONS
        )
        
        # Big play (20+ yards)
        big_play_result = PlayResult(
            outcome="pass_completion",
            yards=35,
            time_elapsed=18.0,
            achieved_first_down=True
        )
        
        aggregator.record_play_result(
            play_result=big_play_result,
            possessing_team_id=TeamIDs.SAN_FRANCISCO_49ERS
        )
        
        # Verify special situation tracking
        assert aggregator.game_stats.turnovers == 1
        assert aggregator.game_stats.penalty_plays == 1
        assert aggregator.game_stats.total_penalty_yards == 5
        assert aggregator.game_stats.big_plays_20_plus == 1
        assert aggregator.game_stats.first_downs_total == 1
    
    def test_fourth_down_tracking(self, aggregator):
        """Test fourth down attempt and conversion tracking"""
        # Fourth down attempt - conversion
        fourth_down_success = PlayResult(
            outcome="rush",
            yards=8,
            time_elapsed=25.0,
            achieved_first_down=True
        )
        
        aggregator.record_play_result(
            play_result=fourth_down_success,
            possessing_team_id=TeamIDs.DETROIT_LIONS,
            down=4,
            yards_to_go=6,
            field_position=55
        )
        
        # Fourth down attempt - failure
        fourth_down_failure = PlayResult(
            outcome="rush",
            yards=2,
            time_elapsed=22.0,
            achieved_first_down=False
        )
        
        aggregator.record_play_result(
            play_result=fourth_down_failure,
            possessing_team_id=TeamIDs.SAN_FRANCISCO_49ERS,
            down=4,
            yards_to_go=5,
            field_position=40
        )
        
        # Verify fourth down tracking
        assert aggregator.game_stats.fourth_down_attempts == 2
        assert aggregator.game_stats.fourth_down_conversions == 1
    
    def test_red_zone_tracking(self, aggregator):
        """Test red zone attempt and scoring tracking"""
        # Red zone scoring play
        red_zone_score = PlayResult(
            outcome="passing_touchdown",
            yards=12,
            points=6,
            time_elapsed=18.0,
            is_scoring_play=True
        )
        
        aggregator.record_play_result(
            play_result=red_zone_score,
            possessing_team_id=TeamIDs.DETROIT_LIONS,
            down=2,
            yards_to_go=8,
            field_position=88  # 12 yards from goal
        )
        
        # Red zone attempt without scoring
        red_zone_attempt = PlayResult(
            outcome="rush",
            yards=3,
            time_elapsed=20.0,
            is_scoring_play=False
        )
        
        aggregator.record_play_result(
            play_result=red_zone_attempt,
            possessing_team_id=TeamIDs.SAN_FRANCISCO_49ERS,
            down=1,
            yards_to_go=10,
            field_position=85  # 15 yards from goal
        )
        
        # Verify red zone tracking
        assert aggregator.game_stats.red_zone_attempts == 2
        assert aggregator.game_stats.red_zone_scores == 1
    
    def test_drive_completion_tracking(self, aggregator):
        """Test drive completion recording"""
        aggregator.record_drive_completion("touchdown", TeamIDs.DETROIT_LIONS)
        aggregator.record_drive_completion("field_goal", TeamIDs.SAN_FRANCISCO_49ERS)
        aggregator.record_drive_completion("punt", TeamIDs.DETROIT_LIONS)
        
        assert aggregator.get_drives_completed() == 3
        assert aggregator.game_stats.total_drives_completed == 3
    
    def test_finalize_game(self, aggregator):
        """Test game finalization with final score"""
        final_score = {
            TeamIDs.DETROIT_LIONS: 24,
            TeamIDs.SAN_FRANCISCO_49ERS: 21
        }
        
        aggregator.finalize_game(final_score)
        
        assert aggregator.game_stats.final_score == final_score
        assert aggregator.game_stats.winner_team_id == TeamIDs.DETROIT_LIONS
    
    def test_finalize_game_tie(self, aggregator):
        """Test game finalization with tie score"""
        final_score = {
            TeamIDs.DETROIT_LIONS: 21,
            TeamIDs.SAN_FRANCISCO_49ERS: 21
        }
        
        aggregator.finalize_game(final_score)
        
        assert aggregator.game_stats.final_score == final_score
        assert aggregator.game_stats.winner_team_id is None  # Tie game
    
    def test_get_player_statistics(self, aggregator):
        """Test player statistics retrieval"""
        # Mock the PlayerStatsAccumulator response
        mock_player_stats = [
            PlayerStats(player_name="Lions QB", player_number=9, position="QB", passing_yards=250),
            PlayerStats(player_name="Lions RB", player_number=32, position="RB", rushing_yards=120)
        ]
        aggregator.player_stats.get_all_players_with_stats = Mock(return_value=mock_player_stats)
        
        # Test all players
        all_players = aggregator.get_player_statistics()
        assert len(all_players) == 2
        assert all_players[0].player_name == "Lions QB"
        
        # Test filtered by player name
        filtered_players = aggregator.get_player_statistics(player_name="QB")
        assert len(filtered_players) == 1
        assert filtered_players[0].position == "QB"
    
    def test_get_team_statistics(self, aggregator):
        """Test team statistics retrieval"""
        # Mock the TeamStatsAccumulator response
        mock_team_stats = TeamStats(team_id=TeamIDs.DETROIT_LIONS, total_yards=350, touchdowns=3)
        aggregator.team_stats.get_team_stats = Mock(return_value=mock_team_stats)
        
        team_stats = aggregator.get_team_statistics(TeamIDs.DETROIT_LIONS)
        
        assert team_stats.team_id == TeamIDs.DETROIT_LIONS
        assert team_stats.total_yards == 350
        assert team_stats.touchdowns == 3
        aggregator.team_stats.get_team_stats.assert_called_once_with(TeamIDs.DETROIT_LIONS)
    
    def test_get_game_statistics(self, aggregator):
        """Test comprehensive game statistics retrieval"""
        # Set up some mock data
        aggregator.player_stats.get_player_count = Mock(return_value=22)
        aggregator.team_stats.get_team_stats = Mock(return_value=TeamStats(team_id=TeamIDs.DETROIT_LIONS))
        
        # Record some plays to have statistics
        aggregator._plays_processed = 5
        aggregator._drives_completed = 2
        aggregator.game_stats.touchdowns = 1
        
        game_stats = aggregator.get_game_statistics()
        
        assert "game_info" in game_stats
        assert "statistics_summary" in game_stats
        assert game_stats["statistics_summary"]["total_players_with_stats"] == 22
        assert game_stats["statistics_summary"]["plays_processed"] == 5
        assert game_stats["statistics_summary"]["drives_completed"] == 2
    
    def test_get_all_statistics(self, aggregator):
        """Test comprehensive statistics package retrieval"""
        # Mock components
        aggregator.player_stats.get_player_count = Mock(return_value=15)
        aggregator.player_stats.get_plays_processed = Mock(return_value=8)
        aggregator.team_stats.get_team_count = Mock(return_value=2)
        aggregator.team_stats.get_plays_processed = Mock(return_value=8)
        aggregator.get_player_statistics = Mock(return_value=[
            PlayerStats(player_name="Test Player", player_number=1, position="QB")
        ])
        aggregator.get_team_statistics = Mock(return_value=TeamStats(team_id=1))
        
        # Set some internal state
        aggregator._plays_processed = 8
        aggregator._drives_completed = 3
        
        all_stats = aggregator.get_all_statistics()
        
        assert "game_info" in all_stats
        assert "player_statistics" in all_stats
        assert "team_statistics" in all_stats
        assert "summary" in all_stats
        
        assert all_stats["summary"]["total_plays_recorded"] == 8
        assert all_stats["summary"]["total_drives_completed"] == 3
        assert all_stats["summary"]["statistics_complete"] is True
        assert all_stats["player_statistics"]["total_players"] == 15
        assert all_stats["team_statistics"]["total_teams"] == 2
    
    def test_reset(self, aggregator):
        """Test statistics reset functionality"""
        # Set up some state
        aggregator._plays_processed = 10
        aggregator._drives_completed = 4
        aggregator.game_stats.touchdowns = 2
        
        # Mock the reset methods of components
        aggregator.player_stats.reset = Mock()
        aggregator.team_stats.reset = Mock()
        
        # Reset
        aggregator.reset()
        
        # Verify reset
        assert aggregator._plays_processed == 0
        assert aggregator._drives_completed == 0
        assert aggregator.game_stats.touchdowns == 0
        aggregator.player_stats.reset.assert_called_once()
        aggregator.team_stats.reset.assert_called_once()
    
    def test_integration_with_existing_components(self, aggregator):
        """Test integration with real PlayerStatsAccumulator and TeamStatsAccumulator"""
        # Create a play result with mock detailed stats
        mock_stats_summary = PlayStatsSummary(
            play_type=PlayType.RUN,
            yards_gained=7,
            time_elapsed=25.0
        )
        
        # Add some player stats to the summary
        player_stat = PlayerStats(
            player_name="Lions RB",
            player_number=32,
            position="RB",
            carries=1,
            rushing_yards=7
        )
        mock_stats_summary.add_player_stats(player_stat)
        
        play_result = PlayResult(
            outcome="rush",
            yards=7,
            time_elapsed=25.0,
            player_stats_summary=mock_stats_summary
        )
        
        # Record the play
        aggregator.record_play_result(
            play_result=play_result,
            possessing_team_id=TeamIDs.DETROIT_LIONS
        )
        
        # Verify integration worked
        assert aggregator.get_plays_processed() == 1
        assert aggregator.player_stats.get_plays_processed() == 1
        assert aggregator.team_stats.get_plays_processed() == 1
        
        # Check that player stats were recorded
        all_players = aggregator.player_stats.get_all_players_with_stats()
        assert len(all_players) > 0
        
        # Check that team stats were recorded
        team_stats = aggregator.team_stats.get_team_stats(TeamIDs.DETROIT_LIONS)
        assert team_stats is not None


if __name__ == "__main__":
    pytest.main([__file__])