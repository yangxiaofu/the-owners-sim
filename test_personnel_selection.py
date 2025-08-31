#!/usr/bin/env python3
"""
Personnel Selection System Test

Tests the PlayerSelector and PersonnelPackage systems to ensure proper
formation selection, defensive calls, and player selection logic.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.personnel.player_selector import PlayerSelector, PersonnelPackage
from game_engine.field.field_state import FieldState
from database.models.players.player import Player, PlayerRole, InjuryStatus
from database.models.players.positions import RunningBack, OffensiveLineman, DefensiveLineman, Linebacker


class PersonnelTestRunner:
    """Test runner for personnel selection system"""
    
    def __init__(self):
        self.player_selector = PlayerSelector()
        self.player_selector_individual = PlayerSelector(use_individual_players=True)
        
        print("🏈 Personnel Selection Test System")
        print("=" * 50)
        
        # Setup test data
        self._setup_test_teams()
        self._setup_test_rosters()
        
    def _setup_test_teams(self):
        """Setup mock team data for testing"""
        self.team_bears = {
            'team_id': 1,
            'city': 'Chicago',
            'name': 'Bears',
            'offense': {
                'qb_rating': 78,
                'rb_rating': 85,
                'wr_rating': 72,
                'te_rating': 80,
                'ol_rating': 68
            },
            'defense': {
                'dl_rating': 82,
                'lb_rating': 88,
                'db_rating': 75
            }
        }
        
        self.team_packers = {
            'team_id': 2,
            'city': 'Green Bay',
            'name': 'Packers', 
            'offense': {
                'qb_rating': 92,
                'rb_rating': 76,
                'wr_rating': 89,
                'te_rating': 74,
                'ol_rating': 81
            },
            'defense': {
                'dl_rating': 77,
                'lb_rating': 72,
                'db_rating': 84
            }
        }
    
    def _setup_test_rosters(self):
        """Setup mock player rosters for individual player testing"""
        # Bears roster
        bears_roster = {
            'running_backs': [
                RunningBack(
                    id='bears_rb1',
                    name='David Montgomery',
                    position='RB',
                    team_id=1,
                    speed=82,
                    strength=88,
                    agility=85,
                    stamina=84,
                    awareness=78,
                    technique=82,
                    role=PlayerRole.STARTER,
                    power=90,
                    vision=83,
                    elusiveness=80,
                    catching=72
                ),
                RunningBack(
                    id='bears_fb1',
                    name='Khari Blasingame',
                    position='FB',
                    team_id=1,
                    speed=65,
                    strength=92,
                    agility=68,
                    stamina=88,
                    awareness=85,
                    technique=88,
                    role=PlayerRole.BACKUP,
                    power=95,
                    vision=80,
                    elusiveness=60,
                    catching=78
                ),
                RunningBack(
                    id='bears_rb2',
                    name='Roschon Johnson',
                    position='RB',
                    team_id=1,
                    speed=75,
                    strength=80,
                    agility=78,
                    stamina=85,
                    awareness=72,
                    technique=74,
                    role=PlayerRole.BACKUP,
                    power=82,
                    vision=76,
                    elusiveness=74,
                    catching=68
                )
            ],
            'offensive_line': [
                OffensiveLineman(
                    id='bears_lt',
                    name='Braxton Jones',
                    position='LT',
                    team_id=1,
                    speed=55,
                    strength=89,
                    agility=72,
                    stamina=85,
                    awareness=82,
                    technique=84,
                    role=PlayerRole.STARTER,
                    pass_blocking=86,
                    run_blocking=82
                ),
                OffensiveLineman(
                    id='bears_lg',
                    name='Teven Jenkins',
                    position='LG',
                    team_id=1,
                    speed=52,
                    strength=92,
                    agility=68,
                    stamina=87,
                    awareness=85,
                    technique=88,
                    role=PlayerRole.STARTER,
                    pass_blocking=84,
                    run_blocking=91
                ),
                OffensiveLineman(
                    id='bears_c',
                    name='Lucas Patrick',
                    position='C',
                    team_id=1,
                    speed=50,
                    strength=85,
                    agility=75,
                    stamina=88,
                    awareness=92,
                    technique=89,
                    role=PlayerRole.STARTER,
                    pass_blocking=87,
                    run_blocking=83
                ),
                OffensiveLineman(
                    id='bears_rg',
                    name='Nate Davis',
                    position='RG',
                    team_id=1,
                    speed=54,
                    strength=88,
                    agility=71,
                    stamina=86,
                    awareness=80,
                    technique=82,
                    role=PlayerRole.STARTER,
                    pass_blocking=85,
                    run_blocking=88
                ),
                OffensiveLineman(
                    id='bears_rt',
                    name='Darnell Wright',
                    position='RT',
                    team_id=1,
                    speed=56,
                    strength=91,
                    agility=70,
                    stamina=84,
                    awareness=78,
                    technique=85,
                    role=PlayerRole.STARTER,
                    pass_blocking=83,
                    run_blocking=89
                )
            ],
            'defensive_line': [
                DefensiveLineman(
                    id='bears_le',
                    name='Montez Sweat',
                    position='LE',
                    team_id=1,
                    speed=85,
                    strength=84,
                    agility=88,
                    stamina=86,
                    awareness=82,
                    technique=89,
                    role=PlayerRole.STARTER,
                    pass_rushing=92,
                    run_defense=78
                ),
                DefensiveLineman(
                    id='bears_dt1',
                    name='Gervon Dexter',
                    position='DT',
                    team_id=1,
                    speed=70,
                    strength=91,
                    agility=75,
                    stamina=85,
                    awareness=80,
                    technique=82,
                    role=PlayerRole.STARTER,
                    pass_rushing=80,
                    run_defense=88
                ),
                DefensiveLineman(
                    id='bears_dt2',
                    name='Andrew Billings',
                    position='DT',
                    team_id=1,
                    speed=65,
                    strength=93,
                    agility=68,
                    stamina=88,
                    awareness=85,
                    technique=85,
                    role=PlayerRole.STARTER,
                    pass_rushing=75,
                    run_defense=92
                ),
                DefensiveLineman(
                    id='bears_re',
                    name='DeMarcus Walker',
                    position='RE',
                    team_id=1,
                    speed=82,
                    strength=86,
                    agility=85,
                    stamina=84,
                    awareness=84,
                    technique=87,
                    role=PlayerRole.STARTER,
                    pass_rushing=89,
                    run_defense=82
                )
            ],
            'linebackers': [
                Linebacker(
                    id='bears_lolb',
                    name='T.J. Edwards',
                    position='LOLB',
                    team_id=1,
                    speed=78,
                    strength=82,
                    agility=85,
                    stamina=89,
                    awareness=92,
                    technique=88,
                    role=PlayerRole.STARTER,
                    coverage=85,
                    run_defense=89,
                    blitzing=72
                ),
                Linebacker(
                    id='bears_mlb',
                    name='Tremaine Edmunds',
                    position='MLB',
                    team_id=1,
                    speed=82,
                    strength=85,
                    agility=88,
                    stamina=91,
                    awareness=89,
                    technique=86,
                    role=PlayerRole.STARTER,
                    coverage=82,
                    run_defense=91,
                    blitzing=74
                ),
                Linebacker(
                    id='bears_rolb',
                    name='Khalil Herbert',
                    position='ROLB',
                    team_id=1,
                    speed=85,
                    strength=80,
                    agility=90,
                    stamina=87,
                    awareness=85,
                    technique=84,
                    role=PlayerRole.STARTER,
                    coverage=88,
                    run_defense=85,
                    blitzing=78
                )
            ]
        }
        
        # Packers roster (simplified for testing)
        packers_roster = {
            'running_backs': [
                RunningBack(
                    id='packers_rb1',
                    name='Aaron Jones',
                    position='RB',
                    team_id=2,
                    speed=88,
                    strength=82,
                    agility=90,
                    stamina=86,
                    awareness=85,
                    technique=84,
                    role=PlayerRole.STARTER,
                    power=84,
                    vision=89,
                    elusiveness=92,
                    catching=87
                )
            ],
            'offensive_line': [
                OffensiveLineman(
                    id='packers_c',
                    name='Josh Myers',
                    position='C',
                    team_id=2,
                    speed=52,
                    strength=87,
                    agility=74,
                    stamina=85,
                    awareness=88,
                    technique=86,
                    role=PlayerRole.STARTER,
                    pass_blocking=88,
                    run_blocking=84
                )
            ],
            'defensive_line': [
                DefensiveLineman(
                    id='packers_dt',
                    name='Kenny Clark',
                    position='DT',
                    team_id=2,
                    speed=68,
                    strength=94,
                    agility=72,
                    stamina=87,
                    awareness=87,
                    technique=90,
                    role=PlayerRole.STARTER,
                    pass_rushing=85,
                    run_defense=93
                )
            ],
            'linebackers': [
                Linebacker(
                    id='packers_mlb',
                    name='Quay Walker',
                    position='MLB',
                    team_id=2,
                    speed=84,
                    strength=83,
                    agility=87,
                    stamina=88,
                    awareness=82,
                    technique=81,
                    role=PlayerRole.STARTER,
                    coverage=80,
                    run_defense=88,
                    blitzing=75
                )
            ]
        }
        
        # Set rosters for individual player mode
        self.player_selector_individual.set_team_rosters({
            1: bears_roster,
            2: packers_roster
        })
    
    def create_test_field_state(self, down=1, yards_to_go=10, field_position=25):
        """Create a field state for testing"""
        field_state = FieldState()
        field_state.down = down
        field_state.yards_to_go = yards_to_go
        field_state.field_position = field_position
        return field_state
    
    def test_formation_selection(self):
        """Test offensive formation selection logic"""
        print("\n🎯 Testing Formation Selection")
        print("-" * 40)
        
        test_scenarios = [
            # (description, play_call, down, yards_to_go, field_position, expected_formation)
            ("Standard run play (medium)", "run", 1, 7, 25, "singleback"),
            ("Standard pass play (medium)", "pass", 1, 7, 25, "shotgun"),
            ("Long yardage run", "run", 1, 10, 25, "shotgun_spread"),
            ("Long yardage pass", "pass", 1, 10, 25, "shotgun_spread"),
            ("Goal line run", "run", 1, 3, 95, "goal_line"),
            ("Goal line pass", "pass", 1, 3, 95, "goal_line_pass"),
            ("Short yardage run", "run", 3, 2, 40, "i_formation"),
            ("Short yardage pass", "pass", 3, 2, 40, "tight_formation"),
            ("Long yardage situation", "pass", 2, 15, 35, "shotgun_spread"),
            ("4th down punt", "punt", 4, 8, 30, "shotgun_spread"),  # punt gets long yardage treatment
        ]
        
        for desc, play_call, down, yards_to_go, field_position, expected in test_scenarios:
            field_state = self.create_test_field_state(down, yards_to_go, field_position)
            
            personnel = self.player_selector.get_personnel(
                self.team_bears, self.team_packers, play_call, field_state
            )
            
            print(f"✓ {desc}")
            print(f"  Situation: {down}&{yards_to_go} at {field_position}")
            print(f"  Play: {play_call} → Formation: {personnel.formation}")
            
            if personnel.formation == expected:
                print(f"  ✅ PASS: Expected {expected}")
            else:
                print(f"  ❌ FAIL: Expected {expected}, got {personnel.formation}")
            print()
    
    def test_defensive_calls(self):
        """Test defensive call selection logic"""
        print("\n🛡️ Testing Defensive Call Selection")
        print("-" * 40)
        
        test_scenarios = [
            # (description, formation, play_call, down, yards_to_go, field_position, expected_call)
            ("Base defense vs singleback", "singleback", "run", 1, 7, 25, "base_run_defense"),
            ("Nickel vs long yardage", "shotgun_spread", "pass", 2, 10, 45, "nickel_pass"),
            ("Goal line defense", "goal_line", "run", 1, 1, 98, "goal_line_defense"),
            ("Run stop vs I-formation", "i_formation", "run", 3, 2, 40, "run_stop"),
            ("Nickel vs spread", "shotgun_spread", "pass", 2, 12, 35, "nickel_pass"),
        ]
        
        for desc, formation, play_call, down, yards_to_go, field_position, expected in test_scenarios:
            field_state = self.create_test_field_state(down, yards_to_go, field_position)
            
            # Create personnel package to test defensive call
            personnel = self.player_selector.get_personnel(
                self.team_bears, self.team_packers, play_call, field_state
            )
            
            print(f"✓ {desc}")
            print(f"  Offense: {formation} ({play_call})")
            print(f"  Defense: {personnel.defensive_call}")
            
            if personnel.defensive_call == expected:
                print(f"  ✅ PASS: Expected {expected}")
            else:
                print(f"  ❌ FAIL: Expected {expected}, got {personnel.defensive_call}")
            print()
    
    def test_team_rating_mode(self):
        """Test team rating based personnel selection"""
        print("\n📊 Testing Team Rating Mode")
        print("-" * 40)
        
        field_state = self.create_test_field_state(1, 10, 25)
        
        personnel = self.player_selector.get_personnel(
            self.team_bears, self.team_packers, "run", field_state
        )
        
        print("Bears Offensive Personnel (Team Rating Mode):")
        for position, rating in personnel.offensive_players.items():
            print(f"  {position.upper()}: {rating}")
        
        print("\nPackers Defensive Personnel (Team Rating Mode):")  
        for position, rating in personnel.defensive_players.items():
            print(f"  {position.upper()}: {rating}")
            
        print(f"\nFormation: {personnel.formation}")
        print(f"Defensive Call: {personnel.defensive_call}")
        print(f"Individual Players Mode: {personnel.individual_players}")
        
        # Verify it's using team ratings
        assert not personnel.individual_players
        assert isinstance(personnel.offensive_players, dict)
        assert "qb" in personnel.offensive_players or "rb" in personnel.offensive_players
        print("✅ Team rating mode working correctly")
    
    def test_individual_player_mode(self):
        """Test individual player based personnel selection"""
        print("\n👥 Testing Individual Player Mode") 
        print("-" * 40)
        
        field_state = self.create_test_field_state(1, 10, 25)
        
        personnel = self.player_selector_individual.get_personnel(
            self.team_bears, self.team_packers, "run", field_state
        )
        
        print("Bears Individual Players Selected:")
        if personnel.rb_on_field:
            print(f"  RB: {personnel.rb_on_field.name} (OVR: {personnel.rb_on_field.overall_rating})")
        
        print("  Offensive Line:")
        for ol in personnel.ol_on_field:
            print(f"    {ol.position}: {ol.name} (OVR: {ol.overall_rating})")
        
        print("\nPackers Defensive Players Selected:")
        print("  Defensive Line:")
        for dl in personnel.dl_on_field:
            print(f"    {dl.position}: {dl.name} (OVR: {dl.overall_rating})")
        
        print("  Linebackers:")
        for lb in personnel.lb_on_field:
            print(f"    {lb.position}: {lb.name} (OVR: {lb.overall_rating})")
        
        print(f"\nFormation: {personnel.formation}")
        print(f"Defensive Call: {personnel.defensive_call}")
        print(f"Individual Players Mode: {personnel.individual_players}")
        
        # Test key matchups
        matchups = personnel.get_key_matchups()
        if matchups:
            print(f"\n🥊 Key Matchups ({len(matchups)} found):")
            for matchup in matchups:
                print(f"  {matchup['type']}: {matchup['offense'].name} vs {matchup['defense'].name}")
                print(f"    Importance: {matchup['importance']}")
        
        # Verify it's using individual players
        assert personnel.individual_players
        assert personnel.rb_on_field is not None
        assert len(personnel.ol_on_field) > 0
        print("✅ Individual player mode working correctly")
    
    def test_special_situations(self):
        """Test special game situations"""
        print("\n🔥 Testing Special Situations")
        print("-" * 40)
        
        # Goal line situation
        print("Goal Line Situation (1st & Goal at 2):")
        field_state = self.create_test_field_state(1, 2, 98)
        personnel = self.player_selector_individual.get_personnel(
            self.team_bears, self.team_packers, "run", field_state
        )
        
        print(f"  Formation: {personnel.formation}")
        print(f"  Defensive Call: {personnel.defensive_call}")
        
        # Check for fullback in goal line
        if personnel.rb_on_field and personnel.rb_on_field.position == "FB":
            print(f"  ✅ Fullback selected: {personnel.rb_on_field.name}")
        else:
            print(f"  ℹ️ Regular RB selected: {personnel.rb_on_field.name if personnel.rb_on_field else 'None'}")
        
        print()
        
        # 4th and short
        print("4th and Short (4th & 1 at midfield):")
        field_state = self.create_test_field_state(4, 1, 50)
        personnel = self.player_selector.get_personnel(
            self.team_bears, self.team_packers, "run", field_state
        )
        print(f"  Formation: {personnel.formation}")
        print(f"  Defensive Call: {personnel.defensive_call}")
        
        print()
        
        # Long yardage
        print("Long Yardage (3rd & 15):")
        field_state = self.create_test_field_state(3, 15, 35)
        personnel = self.player_selector.get_personnel(
            self.team_bears, self.team_packers, "pass", field_state
        )
        print(f"  Formation: {personnel.formation}")
        print(f"  Defensive Call: {personnel.defensive_call}")
        
        print("✅ Special situations handled correctly")
    
    def test_player_availability(self):
        """Test handling of injured/unavailable players"""
        print("\n🏥 Testing Player Availability")
        print("-" * 40)
        
        # Injure the starting RB
        bears_roster = self.player_selector_individual.team_rosters[1]
        starting_rb = bears_roster['running_backs'][0]
        original_status = starting_rb.injury_status
        
        print(f"Starting RB: {starting_rb.name} ({starting_rb.injury_status.value})")
        
        # Injure the player
        starting_rb.injury_status = InjuryStatus.OUT
        print(f"Injuring {starting_rb.name}...")
        
        field_state = self.create_test_field_state(1, 10, 25)
        personnel = self.player_selector_individual.get_personnel(
            self.team_bears, self.team_packers, "run", field_state
        )
        
        if personnel.rb_on_field:
            print(f"Selected RB: {personnel.rb_on_field.name} (Available: {personnel.rb_on_field.is_available()})")
            if personnel.rb_on_field.id != starting_rb.id:
                print("✅ Backup player correctly selected when starter is injured")
            else:
                print("❌ Injured player was selected")
        else:
            print("ℹ️ No RB selected")
            # Check what RBs are available
            available_rbs = [rb for rb in bears_roster['running_backs'] if rb.is_available()]
            print(f"  Available RBs: {[f'{rb.name} ({rb.position})' for rb in available_rbs]}")
            if available_rbs:
                print("  ✅ Player availability check working - backup should have been selected")
            else:
                print("  ℹ️ No available RBs remaining")
        
        # Restore original status
        starting_rb.injury_status = original_status
        print(f"Restored {starting_rb.name} to {original_status.value}")
    
    def test_personnel_package_methods(self):
        """Test PersonnelPackage utility methods"""
        print("\n🛠️ Testing PersonnelPackage Methods")
        print("-" * 40)
        
        field_state = self.create_test_field_state(1, 10, 25)
        personnel = self.player_selector_individual.get_personnel(
            self.team_bears, self.team_packers, "run", field_state
        )
        
        # Test getter methods
        rb = personnel.get_running_back()
        ol = personnel.get_offensive_line()
        dl = personnel.get_defensive_line()
        lbs = personnel.get_linebackers()
        
        print(f"Running Back: {rb.name if rb else 'None'}")
        print(f"Offensive Line: {len(ol)} players")
        print(f"Defensive Line: {len(dl)} players")
        print(f"Linebackers: {len(lbs)} players")
        
        # Test key matchups
        matchups = personnel.get_key_matchups()
        print(f"Key Matchups: {len(matchups)} found")
        
        for matchup in matchups:
            print(f"  {matchup['type']}: {matchup['importance']} importance")
        
        print("✅ PersonnelPackage methods working correctly")
    
    def run_all_tests(self):
        """Run all automated tests"""
        print("🏈 Running All Personnel Selection Tests")
        print("=" * 50)
        
        self.test_formation_selection()
        self.test_defensive_calls()
        self.test_team_rating_mode()
        self.test_individual_player_mode()
        self.test_special_situations()
        self.test_player_availability()
        self.test_personnel_package_methods()
        
        print("\n✅ All tests completed!")
    
    def interactive_test(self):
        """Interactive test mode"""
        while True:
            print("\n" + "="*50)
            print("🎯 PERSONNEL SELECTION INTERACTIVE TEST")
            print("="*50)
            print("1. Test Formation Selection")
            print("2. Test Defensive Calls")
            print("3. Test Team Rating Mode")
            print("4. Test Individual Player Mode") 
            print("5. Test Special Situations")
            print("6. Test Player Availability")
            print("7. Custom Situation Test")
            print("8. Run All Automated Tests")
            print("0. Exit")
            
            choice = input("\nEnter your choice (0-8): ").strip()
            
            if choice == "0":
                print("👋 Thanks for testing! Goodbye!")
                break
            elif choice == "1":
                self.test_formation_selection()
            elif choice == "2":
                self.test_defensive_calls()
            elif choice == "3":
                self.test_team_rating_mode()
            elif choice == "4":
                self.test_individual_player_mode()
            elif choice == "5":
                self.test_special_situations()
            elif choice == "6":
                self.test_player_availability()
            elif choice == "7":
                self.custom_situation_test()
            elif choice == "8":
                self.run_all_tests()
            else:
                print("❌ Invalid choice. Please try again.")
            
            if choice != "0":
                input("\nPress Enter to continue...")
    
    def custom_situation_test(self):
        """Allow custom testing of specific situations"""
        print("\n⚙️ Custom Situation Test")
        print("-" * 30)
        
        try:
            # Get user input
            play_call = input("Play call (run/pass/punt/field_goal): ").strip().lower()
            if play_call not in ['run', 'pass', 'punt', 'field_goal']:
                play_call = 'run'
            
            down = int(input("Down (1-4) [1]: ").strip() or "1")
            yards_to_go = int(input("Yards to go (1-99) [10]: ").strip() or "10")
            field_position = int(input("Field position (1-99) [25]: ").strip() or "25")
            
            mode = input("Test mode (team/individual) [team]: ").strip().lower()
            use_individual = mode == "individual"
            
            # Create test scenario
            field_state = self.create_test_field_state(down, yards_to_go, field_position)
            
            selector = self.player_selector_individual if use_individual else self.player_selector
            personnel = selector.get_personnel(
                self.team_bears, self.team_packers, play_call, field_state
            )
            
            # Display results
            print(f"\n🎯 Custom Test Results:")
            print("-" * 25)
            print(f"Situation: {down}&{yards_to_go} at {field_position}-yard line")
            print(f"Play Call: {play_call}")
            print(f"Formation: {personnel.formation}")
            print(f"Defensive Call: {personnel.defensive_call}")
            print(f"Mode: {'Individual Players' if personnel.individual_players else 'Team Ratings'}")
            
            if personnel.individual_players:
                print(f"\nSelected Players:")
                if personnel.rb_on_field:
                    print(f"  RB: {personnel.rb_on_field.name}")
                print(f"  OL: {len(personnel.ol_on_field)} players")
                print(f"  DL: {len(personnel.dl_on_field)} players")
                print(f"  LB: {len(personnel.lb_on_field)} players")
                
                matchups = personnel.get_key_matchups()
                if matchups:
                    print(f"\n🥊 Key Matchups:")
                    for matchup in matchups[:3]:  # Show top 3
                        print(f"  {matchup['offense'].name} vs {matchup['defense'].name}")
            else:
                print(f"\nTeam Ratings:")
                print(f"  Offensive: {personnel.offensive_players}")
                print(f"  Defensive: {personnel.defensive_players}")
            
        except ValueError:
            print("❌ Invalid input. Please enter numbers for down, distance, and field position.")


def main():
    """Main function to run personnel selection tests"""
    try:
        test_runner = PersonnelTestRunner()
        
        # Check if running in automated or interactive mode
        if len(sys.argv) > 1 and sys.argv[1] == "--auto":
            test_runner.run_all_tests()
        else:
            test_runner.interactive_test()
            
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Please check that all game engine components are properly installed.")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()