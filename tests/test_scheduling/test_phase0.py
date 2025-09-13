"""
Phase 0 validation tests for NFL Schedule Generator

Tests the foundational components including data structures,
models, configuration, and utilities.
"""

import pytest
from datetime import datetime, date
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from scheduling.data.division_structure import (
    NFLStructure, Division, Conference, NFL_STRUCTURE
)
from scheduling.data.schedule_models import (
    ScheduledGame, TimeSlot, GameType, WeekSchedule, SeasonSchedule
)
from scheduling.config import (
    ScheduleConfig, ByeWeekConfig, PrimetimeConfig, 
    ScheduleStrategy, DEFAULT_CONFIG
)
from scheduling.utils.date_utils import (
    get_season_start, get_labor_day, week_to_date, 
    GameDay, get_thanksgiving, date_to_week
)
from constants.team_ids import TeamIDs


class TestNFLStructure:
    """Test NFL division structure and team mappings"""
    
    def test_all_teams_mapped(self):
        """Verify all 32 teams are correctly mapped to divisions"""
        structure = NFLStructure()
        
        # Collect all teams
        all_teams = set()
        for division_teams in structure.divisions.values():
            all_teams.update(division_teams)
        
        # Should have exactly 32 teams
        assert len(all_teams) == 32
        assert min(all_teams) == 1
        assert max(all_teams) == 32
    
    def test_division_sizes(self):
        """Each division should have exactly 4 teams"""
        structure = NFLStructure()
        
        for division, teams in structure.divisions.items():
            assert len(teams) == 4, f"{division.value} has {len(teams)} teams"
    
    def test_team_id_consistency(self):
        """Verify team IDs match the TeamIDs constants"""
        structure = NFLStructure()
        
        # Check specific teams are in correct divisions
        nfc_north = structure.divisions[Division.NFC_NORTH]
        assert TeamIDs.DETROIT_LIONS in nfc_north
        assert TeamIDs.GREEN_BAY_PACKERS in nfc_north
        assert TeamIDs.CHICAGO_BEARS in nfc_north
        assert TeamIDs.MINNESOTA_VIKINGS in nfc_north
        
        # Check AFC East
        afc_east = structure.divisions[Division.AFC_EAST]
        assert TeamIDs.BUFFALO_BILLS in afc_east
        assert TeamIDs.NEW_ENGLAND_PATRIOTS in afc_east
    
    def test_team_lookups(self):
        """Test reverse lookup functions"""
        structure = NFLStructure()
        
        # Test division lookup
        lions_div = structure.get_division_for_team(TeamIDs.DETROIT_LIONS)
        assert lions_div == Division.NFC_NORTH
        
        # Test conference lookup
        lions_conf = structure.get_conference_for_team(TeamIDs.DETROIT_LIONS)
        assert lions_conf == Conference.NFC
        
        # Test division opponents
        lions_opponents = structure.get_division_opponents(TeamIDs.DETROIT_LIONS)
        assert len(lions_opponents) == 3
        assert TeamIDs.GREEN_BAY_PACKERS in lions_opponents
        assert TeamIDs.DETROIT_LIONS not in lions_opponents
    
    def test_conference_teams(self):
        """Test getting all teams in a conference"""
        structure = NFLStructure()
        
        afc_teams = structure.get_conference_teams(Conference.AFC)
        nfc_teams = structure.get_conference_teams(Conference.NFC)
        
        assert len(afc_teams) == 16
        assert len(nfc_teams) == 16
        assert set(afc_teams) & set(nfc_teams) == set()  # No overlap
    
    def test_structure_validation(self):
        """Test structure validation"""
        structure = NFLStructure()
        is_valid, errors = structure.validate_structure()
        
        assert is_valid
        assert len(errors) == 0


class TestScheduleModels:
    """Test schedule data models"""
    
    def test_scheduled_game_creation(self):
        """Test creating a scheduled game"""
        game = ScheduledGame(
            game_id="G0001",
            week=1,
            game_date=datetime(2024, 9, 8, 13, 0),
            home_team_id=TeamIDs.DETROIT_LIONS,
            away_team_id=TeamIDs.GREEN_BAY_PACKERS,
            time_slot=TimeSlot.SUNDAY_EARLY,
            game_type=GameType.DIVISION
        )
        
        assert game.game_id == "G0001"
        assert game.week == 1
        assert game.home_team_id == TeamIDs.DETROIT_LIONS
        assert game.away_team_id == TeamIDs.GREEN_BAY_PACKERS
        assert game.is_primetime == False
    
    def test_primetime_detection(self):
        """Test automatic primetime detection"""
        game = ScheduledGame(
            game_id="G0002",
            week=2,
            game_date=datetime(2024, 9, 12, 20, 15),
            home_team_id=TeamIDs.DALLAS_COWBOYS,
            away_team_id=TeamIDs.NEW_YORK_GIANTS,
            time_slot=TimeSlot.TNF,
            game_type=GameType.DIVISION
        )
        
        assert game.is_primetime == True
    
    def test_game_type_detection(self):
        """Test automatic game type detection"""
        # Division game
        div_game = ScheduledGame(
            game_id="G0003",
            week=1,
            game_date=datetime(2024, 9, 8, 13, 0),
            home_team_id=TeamIDs.DETROIT_LIONS,
            away_team_id=TeamIDs.GREEN_BAY_PACKERS,
            time_slot=TimeSlot.SUNDAY_EARLY,
            game_type=None  # Let it auto-detect
        )
        assert div_game.game_type == GameType.DIVISION
        
        # Conference game
        conf_game = ScheduledGame(
            game_id="G0004",
            week=1,
            game_date=datetime(2024, 9, 8, 13, 0),
            home_team_id=TeamIDs.DETROIT_LIONS,  # NFC North
            away_team_id=TeamIDs.DALLAS_COWBOYS,  # NFC East
            time_slot=TimeSlot.SUNDAY_EARLY,
            game_type=None
        )
        assert conf_game.game_type == GameType.CONFERENCE
        
        # Inter-conference game
        inter_game = ScheduledGame(
            game_id="G0005",
            week=1,
            game_date=datetime(2024, 9, 8, 13, 0),
            home_team_id=TeamIDs.DETROIT_LIONS,  # NFC
            away_team_id=TeamIDs.CLEVELAND_BROWNS,  # AFC
            time_slot=TimeSlot.SUNDAY_EARLY,
            game_type=None
        )
        assert inter_game.game_type == GameType.INTER_CONFERENCE
    
    def test_week_schedule(self):
        """Test week schedule management"""
        week = WeekSchedule(week_number=1)
        
        # Add games
        game1 = ScheduledGame(
            game_id="G0001",
            week=1,
            game_date=datetime(2024, 9, 8, 13, 0),
            home_team_id=1,
            away_team_id=2,
            time_slot=TimeSlot.SUNDAY_EARLY,
            game_type=GameType.CONFERENCE
        )
        week.add_game(game1)
        
        # Add bye teams
        week.teams_on_bye.add(3)
        week.teams_on_bye.add(4)
        
        # Test retrieval
        assert len(week.games) == 1
        assert len(week.teams_on_bye) == 2
        
        teams_playing = week.get_teams_playing()
        assert 1 in teams_playing
        assert 2 in teams_playing
        assert 3 not in teams_playing
    
    def test_season_schedule(self):
        """Test season schedule management"""
        schedule = SeasonSchedule(season_year=2024)
        
        # Should initialize 18 weeks
        assert len(schedule.weeks) == 18
        
        # Add a game
        game = ScheduledGame(
            game_id="G0001",
            week=1,
            game_date=datetime(2024, 9, 8, 13, 0),
            home_team_id=TeamIDs.DETROIT_LIONS,
            away_team_id=TeamIDs.GREEN_BAY_PACKERS,
            time_slot=TimeSlot.SUNDAY_EARLY,
            game_type=GameType.DIVISION
        )
        schedule.add_game(game)
        
        # Test retrieval
        lions_games = schedule.get_team_schedule(TeamIDs.DETROIT_LIONS)
        assert len(lions_games) == 1
        assert lions_games[0].game_id == "G0001"
        
        # Test summary stats
        stats = schedule.summary_stats()
        assert stats['total_games'] == 1
        assert stats['division_games'] == 1


class TestConfiguration:
    """Test configuration system"""
    
    def test_default_config(self):
        """Test default configuration creation"""
        config = ScheduleConfig.default_2024()
        
        assert config.season_year == 2024
        assert config.total_weeks == 18
        assert config.games_per_team == 17
        assert config.strategy == ScheduleStrategy.TEMPLATE_BASED
    
    def test_bye_week_config_validation(self):
        """Test bye week configuration validation"""
        # Valid config
        valid_config = ByeWeekConfig(
            start_week=6,
            end_week=14,
            max_teams_per_week=6,
            min_teams_per_week=2
        )
        assert valid_config.validate()
        
        # Invalid config (not enough capacity)
        invalid_config = ByeWeekConfig(
            start_week=10,
            end_week=11,
            max_teams_per_week=2,
            min_teams_per_week=1
        )
        assert not invalid_config.validate()
    
    def test_config_validation(self):
        """Test full configuration validation"""
        config = ScheduleConfig(season_year=2024)
        is_valid, errors = config.validate()
        
        assert is_valid
        assert len(errors) == 0
        
        # Test invalid config
        bad_config = ScheduleConfig(
            season_year=2024,
            total_weeks=17,  # Should be 18
            games_per_team=16  # Should be 17
        )
        is_valid, errors = bad_config.validate()
        
        assert not is_valid
        assert len(errors) > 0
    
    def test_constraint_weights(self):
        """Test constraint weight configuration"""
        config = ScheduleConfig.default_2024()
        weights = config.constraint_weights
        
        # Check default weights
        assert weights.home_away_balance == 10.0
        assert weights.division_spacing == 8.0
        assert weights.bye_week_fairness == 9.0
        
        # Test conversion to dict
        weights_dict = weights.to_dict()
        assert isinstance(weights_dict, dict)
        assert 'home_away_balance' in weights_dict


class TestDateUtils:
    """Test date utility functions"""
    
    def test_labor_day_calculation(self):
        """Test Labor Day calculation"""
        # 2024 Labor Day is September 2
        labor_day_2024 = get_labor_day(2024)
        assert labor_day_2024 == date(2024, 9, 2)
        
        # 2025 Labor Day is September 1
        labor_day_2025 = get_labor_day(2025)
        assert labor_day_2025 == date(2025, 9, 1)
    
    def test_season_start_calculation(self):
        """Test season start date calculation"""
        # 2024 season starts September 5 (Thursday after Labor Day)
        start_2024 = get_season_start(2024)
        assert start_2024 == date(2024, 9, 5)
        assert start_2024.weekday() == 3  # Thursday
    
    def test_week_to_date_conversion(self):
        """Test converting week numbers to dates"""
        # Week 1 Sunday in 2024
        week1_sunday = week_to_date(2024, 1, GameDay.SUNDAY)
        assert week1_sunday == date(2024, 9, 8)
        assert week1_sunday.weekday() == 6  # Sunday
        
        # Week 1 Thursday (season opener)
        week1_thursday = week_to_date(2024, 1, GameDay.THURSDAY)
        assert week1_thursday == date(2024, 9, 5)
        assert week1_thursday.weekday() == 3  # Thursday
    
    def test_date_to_week_conversion(self):
        """Test converting dates to week numbers"""
        # September 8, 2024 is Week 1
        week = date_to_week(date(2024, 9, 8), 2024)
        assert week == 1
        
        # December 29, 2024 should be Week 17
        week = date_to_week(date(2024, 12, 29), 2024)
        assert week == 17
        
        # Before season should return None
        week = date_to_week(date(2024, 8, 1), 2024)
        assert week is None
    
    def test_thanksgiving_calculation(self):
        """Test Thanksgiving date calculation"""
        # 2024 Thanksgiving is November 28
        thanksgiving_2024 = get_thanksgiving(2024)
        assert thanksgiving_2024 == date(2024, 11, 28)
        assert thanksgiving_2024.weekday() == 3  # Thursday
    
    def test_primetime_slot_detection(self):
        """Test primetime slot identification"""
        from scheduling.utils.date_utils import is_primetime_slot
        
        assert is_primetime_slot('TNF') == True
        assert is_primetime_slot('SNF') == True
        assert is_primetime_slot('MNF') == True
        assert is_primetime_slot('Sunday_1PM') == False
        assert is_primetime_slot('Sunday_4PM') == False


class TestIntegration:
    """Integration tests for Phase 0 components"""
    
    def test_full_game_creation_flow(self):
        """Test creating a game from config through to model"""
        # Create config
        config = ScheduleConfig.default_2024()
        
        # Get season start
        season_start = get_season_start(config.season_year)
        
        # Create Week 1 Sunday game
        game_date = week_to_date(config.season_year, 1, GameDay.SUNDAY)
        game_datetime = datetime.combine(game_date, datetime.min.time())
        game_datetime = game_datetime.replace(hour=13, minute=0)  # 1 PM
        
        # Create game
        game = ScheduledGame(
            game_id="TEST001",
            week=1,
            game_date=game_datetime,
            home_team_id=TeamIDs.DETROIT_LIONS,
            away_team_id=TeamIDs.GREEN_BAY_PACKERS,
            time_slot=TimeSlot.SUNDAY_EARLY,
            game_type=GameType.DIVISION
        )
        
        # Verify game properties
        assert game.week == 1
        assert game.game_date.date() == date(2024, 9, 8)
        assert game.is_primetime == False
        assert game.game_type == GameType.DIVISION
        
        # Test conversion to dict
        game_dict = game.to_dict()
        assert game_dict['game_id'] == "TEST001"
        assert game_dict['home_team'] == TeamIDs.DETROIT_LIONS
        
        # Test recreation from dict
        recreated = ScheduledGame.from_dict(game_dict)
        assert recreated.game_id == game.game_id
        assert recreated.home_team_id == game.home_team_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])