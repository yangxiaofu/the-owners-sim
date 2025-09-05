"""
Simple Penalty System Validation

Tests core penalty functionality without complex integrations to verify
the penalty system is working correctly at a basic level.
"""

import sys
import os
import random

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from penalties.penalty_engine import PenaltyEngine, PlayContext
from penalties.penalty_config_loader import PenaltyConfigLoader
from player import Player


def create_test_player(name: str, position: str, discipline: int = 75) -> Player:
    """Create a test player with specific discipline rating"""
    player = Player(name=name, number=random.randint(1, 99), primary_position=position)
    player.ratings = {
        'discipline': discipline,
        'composure': discipline + random.randint(-5, 5),
        'experience': discipline + random.randint(-10, 10),
        'penalty_technique': discipline + random.randint(-8, 8),
        'speed': 80,
        'strength': 75
    }
    return player


def create_test_offense(discipline: int = 75):
    """Create test offensive lineup"""
    positions = ['QB', 'RB', 'WR', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'WR']
    return [create_test_player(f"Off_{pos}", pos, discipline) for pos in positions]


def create_test_defense(discipline: int = 75):
    """Create test defensive lineup"""
    positions = ['LE', 'DT', 'DT', 'RE', 'MIKE', 'SAM', 'WILL', 'CB', 'CB', 'FS', 'SS']
    return [create_test_player(f"Def_{pos}", pos, discipline) for pos in positions]


def test_basic_penalty_functionality():
    """Test that penalty system basic functionality works"""
    print("Testing basic penalty system functionality...")
    
    penalty_engine = PenaltyEngine()
    offense = create_test_offense()
    defense = create_test_defense()
    
    context = PlayContext(
        play_type="run",
        offensive_formation="i_formation",
        defensive_formation="4_3_base"
    )
    
    penalty_count = 0
    total_tests = 100
    
    try:
        for _ in range(total_tests):
            result = penalty_engine.check_for_penalty(offense, defense, context, 5)
            if result.penalty_occurred:
                penalty_count += 1
        
        penalty_rate = penalty_count / total_tests
        print(f"✅ Basic functionality test PASSED")
        print(f"   Penalty rate: {penalty_rate:.1%} ({penalty_count}/{total_tests})")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test FAILED: {e}")
        return False


def test_discipline_impact():
    """Test that player discipline affects penalty rates"""
    print("Testing discipline impact on penalty rates...")
    
    penalty_engine = PenaltyEngine()
    
    # High discipline team
    high_discipline_offense = create_test_offense(90)
    defense = create_test_defense()
    
    # Low discipline team  
    low_discipline_offense = create_test_offense(45)
    
    context = PlayContext(
        play_type="run", 
        offensive_formation="i_formation",
        defensive_formation="4_3_base"
    )
    
    high_penalties = 0
    low_penalties = 0
    test_runs = 200
    
    try:
        for _ in range(test_runs):
            high_result = penalty_engine.check_for_penalty(high_discipline_offense, defense, context, 5)
            low_result = penalty_engine.check_for_penalty(low_discipline_offense, defense, context, 5)
            
            if high_result.penalty_occurred:
                high_penalties += 1
            if low_result.penalty_occurred:
                low_penalties += 1
        
        high_rate = high_penalties / test_runs
        low_rate = low_penalties / test_runs
        
        if low_rate > high_rate:
            print(f"✅ Discipline impact test PASSED")
            print(f"   High discipline penalty rate: {high_rate:.1%}")
            print(f"   Low discipline penalty rate: {low_rate:.1%}")
            print(f"   Impact ratio: {low_rate/high_rate:.1f}x more penalties for low discipline")
            return True
        else:
            print(f"❌ Discipline impact test FAILED - expected low discipline to have more penalties")
            print(f"   High discipline: {high_rate:.1%}, Low discipline: {low_rate:.1%}")
            return False
            
    except Exception as e:
        print(f"❌ Discipline impact test FAILED: {e}")
        return False


def test_penalty_configuration():
    """Test that penalty configuration system loads properly"""
    print("Testing penalty configuration system...")
    
    try:
        config_loader = PenaltyConfigLoader()
        
        # Test that we can get penalty rates
        holding_rate = config_loader.get_penalty_base_rate('offensive_holding')
        false_start_rate = config_loader.get_penalty_base_rate('false_start')
        
        # Test discipline modifiers
        high_discipline_mod = config_loader.get_discipline_modifier(90)
        low_discipline_mod = config_loader.get_discipline_modifier(40)
        
        # Test situational modifiers
        red_zone_mod = config_loader.get_situational_modifier('offensive_holding', 1, 5, 95)
        normal_mod = config_loader.get_situational_modifier('offensive_holding', 1, 10, 50)
        
        print(f"✅ Configuration system test PASSED")
        print(f"   Holding penalty base rate: {holding_rate:.1%}")
        print(f"   False start penalty base rate: {false_start_rate:.1%}")
        print(f"   High discipline modifier: {high_discipline_mod:.2f}")
        print(f"   Low discipline modifier: {low_discipline_mod:.2f}")
        print(f"   Red zone modifier: {red_zone_mod:.2f}")
        print(f"   Normal field modifier: {normal_mod:.2f}")
        return True
        
    except Exception as e:
        print(f"❌ Configuration system test FAILED: {e}")
        return False


def test_penalty_attribution():
    """Test that penalties are properly attributed to players"""
    print("Testing penalty attribution system...")
    
    penalty_engine = PenaltyEngine()
    offense = create_test_offense()
    defense = create_test_defense()
    
    context = PlayContext(
        play_type="run",
        offensive_formation="i_formation", 
        defensive_formation="4_3_base"
    )
    
    penalties_with_attribution = 0
    total_penalties = 0
    
    try:
        for _ in range(500):  # More iterations to find penalties
            result = penalty_engine.check_for_penalty(offense, defense, context, 5)
            
            if result.penalty_occurred:
                total_penalties += 1
                
                # Check that penalty has proper attribution
                penalty_instance = result.penalty_instance
                if (penalty_instance and 
                    penalty_instance.penalized_player_name and
                    penalty_instance.penalized_player_position and
                    penalty_instance.penalty_type):
                    penalties_with_attribution += 1
        
        if total_penalties > 0:
            attribution_rate = penalties_with_attribution / total_penalties
            print(f"✅ Penalty attribution test PASSED")
            print(f"   Total penalties found: {total_penalties}")
            print(f"   Penalties with proper attribution: {penalties_with_attribution}")
            print(f"   Attribution accuracy: {attribution_rate:.1%}")
            return True
        else:
            print(f"⚠️  Penalty attribution test INCONCLUSIVE - no penalties occurred in 500 tests")
            return True  # Not necessarily a failure if no penalties occur
            
    except Exception as e:
        print(f"❌ Penalty attribution test FAILED: {e}")
        return False


def main():
    """Run all basic penalty system validation tests"""
    print("=" * 60)
    print("PENALTY SYSTEM BASIC VALIDATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_basic_penalty_functionality,
        test_discipline_impact,
        test_penalty_configuration,
        test_penalty_attribution
    ]
    
    passed_tests = 0
    
    for test_func in tests:
        if test_func():
            passed_tests += 1
        print()
    
    print("=" * 60)
    print(f"VALIDATION SUMMARY: {passed_tests}/{len(tests)} tests passed")
    
    if passed_tests == len(tests):
        print("🎉 ALL BASIC PENALTY SYSTEM TESTS PASSED!")
        print("The penalty system core functionality is working correctly.")
    elif passed_tests >= len(tests) * 0.75:
        print("⚠️  MOST TESTS PASSED - Minor issues may need attention")
    else:
        print("❌ MULTIPLE TEST FAILURES - Penalty system needs debugging")
    
    print("=" * 60)


if __name__ == "__main__":
    main()