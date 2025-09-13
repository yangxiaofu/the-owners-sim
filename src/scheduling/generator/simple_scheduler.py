"""
Complete Simple NFL Scheduler - YAGNI Implementation

Integrates matchup generation with existing template system to create
complete NFL schedules from scratch.
"""

from typing import List, Tuple
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scheduling.generator.matchup_generator import SimpleMatchupGenerator
from scheduling.template.basic_scheduler import BasicScheduler
from scheduling.template.schedule_template import SeasonSchedule
from scheduling.data.team_data import TeamDataManager


class CompleteScheduler:
    """
    Complete NFL Schedule Generator
    
    Combines Phase 1 (data), Phase 2 (template), and Phase 3 (matchup generation)
    into a single system that can generate complete NFL schedules.
    """
    
    def __init__(self):
        self.matchup_generator = SimpleMatchupGenerator()
        self.basic_scheduler = BasicScheduler()
        self.team_manager = TeamDataManager()
    
    def generate_full_schedule(self, year: int = 2024) -> SeasonSchedule:
        """
        Generate complete NFL schedule from scratch.
        
        Pipeline:
        1. Generate all 272 matchups using simplified NFL rules
        2. Assign matchups to time slots using existing template system
        3. Validate and return complete schedule
        
        Args:
            year: Season year
            
        Returns:
            Complete SeasonSchedule with all games assigned
        """
        print(f"🏈 Generating complete NFL schedule for {year}...")
        
        # Step 1: Generate all required matchups
        print("📊 Step 1: Generating matchups...")
        matchups = self.matchup_generator.generate_season_matchups(year)
        print(f"✅ Generated {len(matchups)} matchups")
        
        # Step 2: Assign matchups to time slots
        print("📅 Step 2: Assigning to time slots...")
        schedule = self.basic_scheduler.schedule_matchups(matchups, year)
        print(f"✅ Assigned {len(schedule.get_assigned_games())} games to slots")
        
        # Step 3: Validate complete schedule
        print("✅ Step 3: Validating schedule...")
        is_valid, errors = schedule.validate()
        if not is_valid:
            print(f"⚠️  Schedule validation found {len(errors)} issues:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more issues")
        else:
            print("✅ Schedule validation passed!")
        
        return schedule
    
    def generate_schedule_summary(self, schedule: SeasonSchedule) -> dict:
        """
        Generate summary statistics for a complete schedule.
        
        Args:
            schedule: Complete season schedule
            
        Returns:
            Dictionary with schedule statistics
        """
        summary = {
            'year': schedule.year,
            'total_slots': schedule.get_total_slots(),
            'assigned_games': len(schedule.get_assigned_games()),
            'empty_slots': len(schedule.get_empty_slots()),
            'primetime_games': len(schedule.get_primetime_games()),
            'team_schedules': {}
        }
        
        # Add per-team statistics
        for team_id in range(1, 33):
            team = self.team_manager.get_team(team_id)
            team_games = schedule.get_team_schedule(team_id)
            home_games, away_games = schedule.get_home_away_balance(team_id)
            
            summary['team_schedules'][team_id] = {
                'team_name': team.full_name,
                'total_games': len(team_games),
                'home_games': home_games,
                'away_games': away_games,
                'primetime_games': len([g for g in team_games if g.is_primetime and g.is_assigned])
            }
        
        return summary
    
    def get_team_schedule_display(self, schedule: SeasonSchedule, team_id: int) -> List[str]:
        """
        Get formatted display of a team's schedule.
        
        Args:
            schedule: Complete season schedule
            team_id: Team to display schedule for
            
        Returns:
            List of formatted schedule strings
        """
        team = self.team_manager.get_team(team_id)
        team_games = schedule.get_team_schedule(team_id)
        
        # Sort by week
        assigned_games = [g for g in team_games if g.is_assigned]
        assigned_games.sort(key=lambda x: x.week)
        
        schedule_lines = [f"📅 {team.full_name} {schedule.year} Schedule"]
        schedule_lines.append("=" * 50)
        
        for game in assigned_games:
            # Determine opponent and location
            if game.home_team_id == team_id:
                opponent = self.team_manager.get_team(game.away_team_id)
                location = "vs"
            else:
                opponent = self.team_manager.get_team(game.home_team_id)
                location = "@"
            
            # Format game info
            slot_type = "PRIMETIME" if game.is_primetime else "REGULAR"
            schedule_lines.append(
                f"Week {game.week:2d} {game.time_slot.value:8s} ({slot_type:9s}): "
                f"{location} {opponent.full_name}"
            )
        
        return schedule_lines
    
    def validate_complete_system(self) -> Tuple[bool, List[str]]:
        """
        Validate that the complete scheduling system is working correctly.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Test matchup generation
            test_matchups = self.matchup_generator.generate_season_matchups(2024)
            if len(test_matchups) != 272:
                issues.append(f"Matchup generation produced {len(test_matchups)} games, expected 272")
            
            # Test schedule generation
            test_schedule = self.basic_scheduler.schedule_matchups(test_matchups[:10], 2024)  # Small test
            if len(test_schedule.get_assigned_games()) == 0:
                issues.append("Basic scheduler failed to assign any games")
            
            # Test team data integration
            if len(self.team_manager) != 32:
                issues.append(f"Team manager has {len(self.team_manager)} teams, expected 32")
            
        except Exception as e:
            issues.append(f"System validation failed with error: {str(e)}")
        
        return len(issues) == 0, issues
    
    def quick_schedule_test(self) -> bool:
        """
        Quick test to verify the system can generate a basic schedule.
        
        Returns:
            True if test passes, False otherwise
        """
        try:
            # Generate small test schedule
            test_matchups = [
                (22, 23),  # Lions @ Packers
                (23, 22),  # Packers @ Lions
                (17, 18),  # Cowboys @ Giants
                (18, 17),  # Giants @ Cowboys
            ]
            
            test_schedule = self.basic_scheduler.schedule_matchups(test_matchups, 2024)
            
            return (len(test_schedule.get_assigned_games()) == 4 and
                    test_schedule.get_total_slots() > 200)
            
        except Exception:
            return False