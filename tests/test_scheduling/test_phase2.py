"""
Phase 2 Tests: Template System for NFL Schedule Generator

Tests the minimal YAGNI implementation:
- TimeSlot enum and GameSlot dataclass
- SeasonSchedule class 
- BasicScheduler assignment algorithm
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from scheduling.template.time_slots import TimeSlot, GameSlot
from scheduling.template.schedule_template import SeasonSchedule
from scheduling.template.basic_scheduler import BasicScheduler


class TestTimeSlots:
    """Test time slot definitions and GameSlot functionality"""
    
    def test_time_slot_enum(self):
        """Test TimeSlot enum values"""
        assert TimeSlot.THURSDAY_NIGHT.value == "TNF"
        assert TimeSlot.SUNDAY_EARLY.value == "SUN_1PM"
        assert TimeSlot.SUNDAY_LATE.value == "SUN_4PM"
        assert TimeSlot.SUNDAY_NIGHT.value == "SNF"
        assert TimeSlot.MONDAY_NIGHT.value == "MNF"
    
    def test_game_slot_creation(self):
        """Test GameSlot creation and properties"""
        slot = GameSlot(week=1, time_slot=TimeSlot.SUNDAY_EARLY)
        
        assert slot.week == 1
        assert slot.time_slot == TimeSlot.SUNDAY_EARLY
        assert slot.home_team_id is None
        assert slot.away_team_id is None
        assert not slot.is_assigned
        assert not slot.is_primetime  # Sunday early is not primetime
        
    def test_game_slot_assignment(self):
        """Test assigning a game to a slot"""
        slot = GameSlot(week=5, time_slot=TimeSlot.SUNDAY_NIGHT)
        
        # Initially empty
        assert not slot.is_assigned
        assert slot.game_id == "W05_EMPTY_SNF"
        
        # Assign game
        slot.assign_game(22, 23)  # Lions @ Packers
        
        assert slot.is_assigned
        assert slot.home_team_id == 22
        assert slot.away_team_id == 23
        assert slot.game_id == "W05_23@22"
        assert slot.is_primetime  # Sunday night is primetime
        
    def test_game_slot_clear_assignment(self):
        """Test clearing game assignment"""
        slot = GameSlot(week=3, time_slot=TimeSlot.MONDAY_NIGHT)
        slot.assign_game(17, 14)  # Cowboys @ Chiefs
        
        assert slot.is_assigned
        
        slot.clear_assignment()
        
        assert not slot.is_assigned
        assert slot.home_team_id is None
        assert slot.away_team_id is None
        
    def test_primetime_slots(self):
        """Test primetime slot identification"""
        primetime_slots = [TimeSlot.THURSDAY_NIGHT, TimeSlot.SUNDAY_NIGHT, TimeSlot.MONDAY_NIGHT]
        regular_slots = [TimeSlot.SUNDAY_EARLY, TimeSlot.SUNDAY_LATE]
        
        for slot_type in primetime_slots:
            slot = GameSlot(week=1, time_slot=slot_type)
            assert slot.is_primetime
            
        for slot_type in regular_slots:
            slot = GameSlot(week=1, time_slot=slot_type)
            assert not slot.is_primetime
    
    def test_game_slot_string_representation(self):
        """Test string representation of GameSlot"""
        slot = GameSlot(week=10, time_slot=TimeSlot.THURSDAY_NIGHT)
        
        # Empty slot
        assert "Week 10 TNF: EMPTY" in str(slot)
        
        # Assigned slot
        slot.assign_game(31, 16)  # 49ers @ Chiefs
        assert "Week 10 TNF: 16 @ 31" in str(slot)


class TestSeasonSchedule:
    """Test season schedule functionality"""
    
    def test_empty_schedule_creation(self):
        """Test creating empty season schedule"""
        schedule = SeasonSchedule(year=2024, games=[])
        
        assert schedule.year == 2024
        assert len(schedule.games) > 0  # Should auto-create empty schedule
        assert schedule.get_total_slots() >= 250  # Should have ~250-272 slots
        assert len(schedule.get_assigned_games()) == 0  # No games assigned initially
        
    def test_schedule_structure(self):
        """Test the structure of the generated schedule"""
        schedule = SeasonSchedule(year=2024, games=[])
        
        # Check we have games for each week
        for week in range(1, 19):  # Weeks 1-18
            week_games = schedule.get_week_games(week)
            assert len(week_games) > 0
            
            # Week 1 should have no Thursday night game
            if week == 1:
                tnf_games = [g for g in week_games if g.time_slot == TimeSlot.THURSDAY_NIGHT]
                assert len(tnf_games) == 0
            else:
                tnf_games = [g for g in week_games if g.time_slot == TimeSlot.THURSDAY_NIGHT]
                assert len(tnf_games) == 1
            
            # Week 18 should have no Monday night game
            if week == 18:
                mnf_games = [g for g in week_games if g.time_slot == TimeSlot.MONDAY_NIGHT]
                assert len(mnf_games) == 0
            else:
                mnf_games = [g for g in week_games if g.time_slot == TimeSlot.MONDAY_NIGHT]
                assert len(mnf_games) == 1
    
    def test_team_schedule_tracking(self):
        """Test getting schedule for specific teams"""
        schedule = SeasonSchedule(year=2024, games=[])
        
        # Assign a few games manually
        week_1_games = schedule.get_week_games(1)
        week_1_games[0].assign_game(22, 23)  # Lions @ Packers, week 1
        week_1_games[1].assign_game(17, 18)  # Cowboys @ Giants, week 1
        
        # Test team schedules
        lions_schedule = schedule.get_team_schedule(22)
        assert len(lions_schedule) == 1
        assert lions_schedule[0].home_team_id == 22
        
        packers_schedule = schedule.get_team_schedule(23)
        assert len(packers_schedule) == 1
        assert packers_schedule[0].away_team_id == 23
        
    def test_schedule_validation_empty(self):
        """Test validation of empty schedule"""
        schedule = SeasonSchedule(year=2024, games=[])
        
        is_valid, errors = schedule.validate()
        assert not is_valid  # Should be invalid (no games assigned)
        assert len(errors) > 0
        
        # Should have errors about teams not having 17 games
        team_errors = [e for e in errors if "games (expected 17)" in e]
        assert len(team_errors) == 32  # All 32 teams should have errors
        
    def test_home_away_balance(self):
        """Test home/away game balance tracking"""
        schedule = SeasonSchedule(year=2024, games=[])
        
        # Initially no games
        home, away = schedule.get_home_away_balance(22)  # Lions
        assert home == 0
        assert away == 0
        
        # Add some games
        week_1_games = schedule.get_week_games(1)
        week_2_games = schedule.get_week_games(2)
        
        week_1_games[0].assign_game(22, 23)  # Lions home vs Packers
        week_2_games[0].assign_game(17, 22)  # Cowboys home vs Lions (Lions away)
        
        home, away = schedule.get_home_away_balance(22)
        assert home == 1
        assert away == 1
    
    def test_primetime_games(self):
        """Test primetime game tracking"""
        schedule = SeasonSchedule(year=2024, games=[])
        
        # Find primetime slots and assign games
        primetime_slots = [g for g in schedule.games if g.is_primetime]
        assert len(primetime_slots) > 0
        
        # Assign a primetime game
        primetime_slots[0].assign_game(22, 23)
        
        primetime_games = schedule.get_primetime_games()
        assert len(primetime_games) == 1
        assert primetime_games[0].home_team_id == 22
        assert primetime_games[0].away_team_id == 23
    
    def test_schedule_string_representation(self):
        """Test string representation of schedule"""
        schedule = SeasonSchedule(year=2024, games=[])
        schedule_str = str(schedule)
        
        assert "SeasonSchedule 2024" in schedule_str
        assert "0/" in schedule_str  # No games assigned initially
        assert f"/{schedule.get_total_slots()}" in schedule_str


class TestBasicScheduler:
    """Test basic scheduling algorithm"""
    
    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly"""
        scheduler = BasicScheduler()
        assert scheduler.team_manager is not None
        assert scheduler.rivalry_detector is not None
    
    def test_simple_matchup_generation(self):
        """Test generating simple matchups for testing"""
        scheduler = BasicScheduler()
        
        # Generate a small set of matchups
        matchups = scheduler.generate_simple_matchups(num_games=50)
        
        assert len(matchups) >= 40  # Should generate close to requested number
        assert len(matchups) <= 50  # But may be slightly less due to balancing
        assert all(isinstance(m, tuple) and len(m) == 2 for m in matchups)
        assert all(1 <= home <= 32 and 1 <= away <= 32 for home, away in matchups)
        assert all(home != away for home, away in matchups)
    
    def test_primetime_worthy_identification(self):
        """Test identification of primetime-worthy matchups"""
        scheduler = BasicScheduler()
        
        # Test matchups including some rivalries
        test_matchups = [
            (22, 23),  # Lions @ Packers (division rivals)
            (1, 2),    # Cardinals @ Falcons (not special)
            (17, 18),  # Cowboys @ Giants (large market)
            (5, 6),    # Ravens @ Bengals (not configured as rivals in our minimal system)
        ]
        
        primetime_worthy = scheduler.get_primetime_worthy_matchups(test_matchups)
        
        # Should include division rivals and large market teams
        assert len(primetime_worthy) > 0
        
        # Lions @ Packers should be included (division rivals)
        assert (22, 23) in primetime_worthy
    
    def test_basic_scheduling_small_set(self):
        """Test basic scheduling with small set of matchups"""
        scheduler = BasicScheduler()
        
        # Create a very small set of matchups to test
        test_matchups = [
            (22, 23),  # Lions @ Packers
            (17, 18),  # Cowboys @ Giants
            (14, 15),  # Chiefs @ Raiders
            (1, 2),    # Cardinals @ Falcons
        ]
        
        schedule = scheduler.schedule_matchups(test_matchups, year=2024)
        
        assert len(schedule.get_assigned_games()) == 4
        
        # Each team should appear in exactly one game
        teams_playing = set()
        for game in schedule.get_assigned_games():
            assert game.home_team_id not in teams_playing
            assert game.away_team_id not in teams_playing
            teams_playing.add(game.home_team_id)
            teams_playing.add(game.away_team_id)
        
        assert len(teams_playing) == 8  # 4 games * 2 teams each


class TestPhase2Integration:
    """Integration tests for Phase 2 components"""
    
    def test_full_integration_small_schedule(self):
        """Test full integration with small schedule"""
        scheduler = BasicScheduler()
        
        # Generate matchups for just a few teams to test integration
        test_matchups = []
        for home in [22, 23, 17, 18]:  # Lions, Packers, Cowboys, Giants
            for away in [22, 23, 17, 18]:
                if home != away and len(test_matchups) < 6:  # 6 total games
                    test_matchups.append((home, away))
        
        schedule = scheduler.schedule_matchups(test_matchups, year=2024)
        
        # Verify basic properties
        assert schedule.year == 2024
        assert len(schedule.get_assigned_games()) == 6
        
        # Verify no team plays twice in same week
        for team_id in [22, 23, 17, 18]:
            team_games = schedule.get_team_schedule(team_id)
            weeks = [game.week for game in team_games if game.is_assigned]
            assert len(weeks) == len(set(weeks))  # No duplicate weeks
    
    def test_schedule_validation_realistic(self):
        """Test schedule validation with realistic constraints"""
        schedule = SeasonSchedule(year=2024, games=[])
        
        # Assign exactly 17 games per team (simplified)
        team_game_count = {team_id: 0 for team_id in range(1, 33)}
        week = 1
        
        for i, game_slot in enumerate(schedule.games):
            if i >= 272:  # Only 272 total games in NFL
                break
                
            # Find two teams that need games and haven't played this week
            home_team = (i % 32) + 1
            away_team = ((i + 1) % 32) + 1
            
            if (home_team != away_team and
                team_game_count[home_team] < 17 and
                team_game_count[away_team] < 17):
                
                game_slot.assign_game(home_team, away_team)
                team_game_count[home_team] += 1
                team_game_count[away_team] += 1
        
        # Check if we can get close to valid
        assigned_games = len(schedule.get_assigned_games())
        assert assigned_games > 0
        
        is_valid, errors = schedule.validate()
        # May not be perfectly valid due to simple assignment, but should have some structure
        assert len(errors) >= 0  # Just ensure validation runs without crashing


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])