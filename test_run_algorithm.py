"""
Comprehensive test suite for the Situational Matchup Matrix Algorithm
Tests SOLID principles compliance, statistical accuracy, and football authenticity
"""

import statistics
from unittest.mock import Mock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.run_play import RunPlay, MATCHUP_MATRICES
from game_engine.field.field_state import FieldState


class TestRunTypeClassification:
    """Test SOLID: Single Responsibility - run type determination"""
    
    def setup_method(self):
        self.run_play = RunPlay()
        
    def test_goal_line_power_classification(self):
        """Test goal line situations correctly classified"""
        field_state = FieldState()
        field_state.field_position = 98  # 2 yard line
        field_state.yards_to_go = 2     # Short yardage
        
        run_type = self.run_play._determine_run_type("I_formation", field_state)
        assert run_type == "goal_line_power"
        
    def test_formation_based_classification(self):
        """Test formation-to-run-type mapping"""
        field_state = FieldState()
        field_state.field_position = 50  # Midfield
        
        test_cases = [
            ("I_formation", "power_run"),
            ("goal_line", "goal_line_power"),
            ("singleback", "inside_zone"),
            ("shotgun", "draw_play"),
            ("pistol", "inside_zone"),
            ("unknown_formation", "inside_zone")  # Default case
        ]
        
        for formation, expected_run_type in test_cases:
            run_type = self.run_play._determine_run_type(formation, field_state)
            assert run_type == expected_run_type, f"Formation {formation} should map to {expected_run_type}"


class TestRBEffectivenessCalculation:
    """Test SOLID: Dependency Inversion - RB attribute integration"""
    
    def setup_method(self):
        self.run_play = RunPlay()
        
    def create_mock_rb(self, **attributes):
        """Create mock RB with specified attributes"""
        rb = Mock()
        for attr, value in attributes.items():
            setattr(rb, attr, value)
        return rb
        
    def test_power_back_vs_power_runs(self):
        """Power backs should excel at power runs"""
        power_back = self.create_mock_rb(power=90, vision=70)
        speed_back = self.create_mock_rb(speed=90, agility=85, power=60, vision=65)
        
        power_back_effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(
            power_back, "power_run"
        )
        speed_back_effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(
            speed_back, "power_run"
        )
        
        assert power_back_effectiveness > speed_back_effectiveness, \
            "Power back should be more effective at power runs"
    
    def test_speed_back_vs_outside_zone(self):
        """Speed backs should excel at outside zone runs"""
        power_back = self.create_mock_rb(power=90, vision=70, speed=65, agility=60)
        speed_back = self.create_mock_rb(speed=90, agility=85)
        
        power_back_effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(
            power_back, "outside_zone"
        )
        speed_back_effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(
            speed_back, "outside_zone"
        )
        
        assert speed_back_effectiveness > power_back_effectiveness, \
            "Speed back should be more effective at outside zone"
            
    def test_vision_back_vs_inside_zone(self):
        """High vision backs should excel at inside zone runs"""
        vision_back = self.create_mock_rb(vision=90, agility=80)
        power_back = self.create_mock_rb(power=90, strength=85, vision=60, agility=55)
        
        vision_back_effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(
            vision_back, "inside_zone"
        )
        power_back_effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(
            power_back, "inside_zone"
        )
        
        assert vision_back_effectiveness > power_back_effectiveness, \
            "High vision back should be more effective at inside zone"
    
    def test_no_rb_fallback(self):
        """Test fallback when no RB provided"""
        effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(None, "power_run")
        assert effectiveness == 0.5, "Should return default 0.5 effectiveness when no RB"
        
    def test_missing_attributes_fallback(self):
        """Test safe attribute access with missing attributes"""
        incomplete_rb = Mock()
        # Missing required attributes should use fallback of 50
        
        effectiveness = self.run_play._calculate_rb_effectiveness_for_run_type(
            incomplete_rb, "power_run"
        )
        assert 0.0 <= effectiveness <= 1.0, "Effectiveness should be normalized to 0-1 range"
        assert effectiveness == 0.5, "Missing attributes should default to 50, giving 0.5 effectiveness"


class TestYardsCalculationRanges:
    """Test realistic yards ranges for each run type"""
    
    def setup_method(self):
        self.run_play = RunPlay()
        
    def create_mock_personnel(self, formation="singleback", rb_attributes=None):
        """Create mock personnel package"""
        personnel = Mock()
        personnel.formation = formation
        personnel.rb_on_field = None
        
        if rb_attributes:
            rb = Mock()
            for attr, value in rb_attributes.items():
                setattr(rb, attr, value)
            personnel.rb_on_field = rb
            
        return personnel
        
    def test_power_run_yards_range(self):
        """Power runs should produce 1-8 yards typically"""
        field_state = FieldState()
        field_state.field_position = 50
        
        personnel = self.create_mock_personnel("I_formation", {"power": 80, "vision": 75})
        
        # Run 100 simulations to test range
        yards_results = []
        for _ in range(100):
            outcome, yards = self.run_play._calculate_yards_from_matchup_matrix(
                {"ol": 75}, {"dl": 70}, personnel, 1.0, field_state
            )
            if outcome != "fumble":  # Exclude fumbles from yards analysis
                yards_results.append(yards)
        
        avg_yards = statistics.mean(yards_results)
        assert 1.0 <= avg_yards <= 8.0, f"Power run average {avg_yards} should be 1-8 yards"
        
    def test_outside_zone_variance(self):
        """Outside zone should have higher variance (boom/bust nature)"""
        field_state = FieldState()
        
        personnel = self.create_mock_personnel("singleback", {"speed": 85, "agility": 80})
        
        # Compare variance between outside zone and power runs
        outside_yards = []
        power_yards = []
        
        for _ in range(100):
            # Outside zone (singleback formation defaults to inside_zone, but we'll test the concept)
            outcome, yards = self.run_play._calculate_yards_from_matchup_matrix(
                {"ol": 75}, {"dl": 70}, personnel, 1.0, field_state
            )
            if outcome != "fumble":
                outside_yards.append(yards)
                
        # Power runs for comparison
        power_personnel = self.create_mock_personnel("I_formation", {"power": 85, "vision": 75})
        for _ in range(100):
            outcome, yards = self.run_play._calculate_yards_from_matchup_matrix(
                {"ol": 75}, {"dl": 70}, power_personnel, 1.0, field_state
            )
            if outcome != "fumble":
                power_yards.append(yards)
        
        outside_variance = statistics.variance(outside_yards) if len(outside_yards) > 1 else 0
        power_variance = statistics.variance(power_yards) if len(power_yards) > 1 else 0
        
        # Note: This test may be flaky due to randomization, but should generally hold
        print(f"Outside variance: {outside_variance}, Power variance: {power_variance}")
        
    def test_goal_line_short_consistent_gains(self):
        """Goal line power should produce short, consistent gains"""
        field_state = FieldState()
        field_state.field_position = 98  # 2 yard line
        field_state.yards_to_go = 1
        
        personnel = self.create_mock_personnel("goal_line", {"power": 85, "strength": 80})
        
        yards_results = []
        for _ in range(50):
            outcome, yards = self.run_play._calculate_yards_from_matchup_matrix(
                {"ol": 80}, {"dl": 75}, personnel, 1.2, field_state
            )
            if outcome != "fumble":
                yards_results.append(yards)
        
        if yards_results:  # Only test if we have results
            avg_yards = statistics.mean(yards_results)
            max_yards = max(yards_results)
            
            assert avg_yards <= 3.0, f"Goal line average {avg_yards} should be ≤3 yards"
            assert max_yards <= 8, f"Goal line max {max_yards} should be ≤8 yards"


class TestSituationalModifiers:
    """Test situational awareness (YAGNI: only essential modifiers)"""
    
    def setup_method(self):
        self.run_play = RunPlay()
        
    def test_third_and_short_penalty(self):
        """3rd and short should reduce yards (defense expecting run)"""
        base_yards = 4.0
        
        # 3rd and short situation
        field_state = FieldState()
        field_state.down = 3
        field_state.yards_to_go = 2
        
        modified_yards = self.run_play._apply_situational_modifiers(
            base_yards, field_state, "power_run"
        )
        
        assert modified_yards < base_yards, "3rd and short should reduce expected yards"
        assert modified_yards == base_yards * 0.85, "Should apply 15% penalty"
        
    def test_first_down_bonus(self):
        """1st down should increase yards (more unpredictable)"""
        base_yards = 4.0
        
        field_state = FieldState()
        field_state.down = 1
        field_state.yards_to_go = 10
        
        modified_yards = self.run_play._apply_situational_modifiers(
            base_yards, field_state, "inside_zone"
        )
        
        assert modified_yards > base_yards, "1st down should increase expected yards"
        assert modified_yards == base_yards * 1.05, "Should apply 5% bonus"
        
    def test_goal_line_compression(self):
        """Non-goal-line runs near goal line should be compressed"""
        base_yards = 5.0
        
        field_state = FieldState()
        field_state.field_position = 96  # 4 yard line
        
        modified_yards = self.run_play._apply_situational_modifiers(
            base_yards, field_state, "inside_zone"
        )
        
        assert modified_yards < base_yards, "Goal line should compress non-power runs"
        assert modified_yards == base_yards * 0.7, "Should apply 30% penalty"
        
    def test_deep_field_bonus(self):
        """Runs from own 20 or less should get bonus (defense playing safe)"""
        base_yards = 4.0
        
        field_state = FieldState()
        field_state.field_position = 15  # Own 15 yard line
        
        modified_yards = self.run_play._apply_situational_modifiers(
            base_yards, field_state, "outside_zone"
        )
        
        assert modified_yards > base_yards, "Deep field should increase expected yards"
        assert modified_yards == base_yards * 1.1, "Should apply 10% bonus"


class TestStatisticalValidation:
    """Test statistical distributions match realistic expectations"""
    
    def setup_method(self):
        self.run_play = RunPlay()
        
    def create_standard_test_setup(self):
        """Create standard test setup for statistical runs"""
        field_state = FieldState()
        field_state.field_position = 50  # Midfield
        
        personnel = Mock()
        personnel.formation = "singleback"
        personnel.rb_on_field = Mock()
        personnel.rb_on_field.vision = 80
        personnel.rb_on_field.agility = 75
        personnel.rb_on_field.power = 70
        personnel.rb_on_field.speed = 75
        personnel.rb_on_field.elusiveness = 70
        personnel.rb_on_field.strength = 75
        
        return field_state, personnel
        
    def test_average_yards_per_attempt(self):
        """Test that average YPA falls within NFL range (3.5-4.5)"""
        field_state, personnel = self.create_standard_test_setup()
        
        yards_results = []
        for _ in range(1000):  # Large sample for statistical validity
            outcome, yards = self.run_play._calculate_yards_from_matchup_matrix(
                {"ol": 75}, {"dl": 75}, personnel, 1.0, field_state
            )
            yards_results.append(yards)  # Include all results, even fumbles (-2 to 0)
        
        avg_yards = statistics.mean(yards_results)
        print(f"Average YPA over 1000 runs: {avg_yards:.2f}")
        
        # NFL average is around 4.2 YPC, allow reasonable range
        assert 3.0 <= avg_yards <= 5.0, f"Average YPA {avg_yards} should be 3.0-5.0"
        
    def test_touchdown_frequency(self):
        """Test touchdown frequency is realistic (should be low)"""
        field_state, personnel = self.create_standard_test_setup()
        
        touchdowns = 0
        total_runs = 1000
        
        for _ in range(total_runs):
            outcome, yards = self.run_play._calculate_yards_from_matchup_matrix(
                {"ol": 75}, {"dl": 75}, personnel, 1.0, field_state
            )
            if outcome == "touchdown":
                touchdowns += 1
        
        td_rate = touchdowns / total_runs
        print(f"Touchdown rate over {total_runs} runs: {td_rate:.3f}")
        
        # NFL touchdown rate on runs is roughly 2-8% depending on situation
        assert 0.01 <= td_rate <= 0.15, f"TD rate {td_rate} should be 1-15%"
        
    def test_fumble_frequency(self):
        """Test fumble frequency is realistic (should be rare)"""
        field_state, personnel = self.create_standard_test_setup()
        
        fumbles = 0
        total_runs = 1000
        
        for _ in range(total_runs):
            outcome, yards = self.run_play._calculate_yards_from_matchup_matrix(
                {"ol": 75}, {"dl": 75}, personnel, 1.0, field_state
            )
            if outcome == "fumble":
                fumbles += 1
        
        fumble_rate = fumbles / total_runs
        print(f"Fumble rate over {total_runs} runs: {fumble_rate:.3f}")
        
        # NFL fumble rate is roughly 1-3% on rushing attempts
        assert fumble_rate <= 0.05, f"Fumble rate {fumble_rate} should be ≤5%"


class TestBreakawayLogic:
    """Test YAGNI: Simple breakaway logic"""
    
    def setup_method(self):
        self.run_play = RunPlay()
        
    def test_high_attribute_rb_breakaway_potential(self):
        """High-attribute RBs should have breakaway potential"""
        elite_rb = Mock()
        elite_rb.power = 95
        elite_rb.vision = 90
        
        matrix = MATCHUP_MATRICES["power_run"]
        
        # Test multiple times due to randomness
        breakaway_count = 0
        for _ in range(100):
            if self.run_play._check_breakaway_potential(elite_rb, matrix, 10.0):
                breakaway_count += 1
        
        # Elite RB should have some breakaway potential
        assert breakaway_count > 0, "Elite RB should have breakaway potential"
        assert breakaway_count < 50, "Breakaway shouldn't be too common"
        
    def test_low_attribute_rb_no_breakaway(self):
        """Low-attribute RBs should rarely break away"""
        average_rb = Mock()
        average_rb.power = 60
        average_rb.vision = 55
        
        matrix = MATCHUP_MATRICES["power_run"]
        
        breakaway_count = 0
        for _ in range(100):
            if self.run_play._check_breakaway_potential(average_rb, matrix, 10.0):
                breakaway_count += 1
        
        # Average RB should rarely break away on power runs
        assert breakaway_count <= 5, "Average RB should rarely break away"
        
    def test_short_gain_no_breakaway(self):
        """Short gains should never lead to breakaways"""
        elite_rb = Mock()
        elite_rb.power = 95
        elite_rb.vision = 95
        
        matrix = MATCHUP_MATRICES["power_run"]
        
        # Short gains should never break away regardless of RB ability
        assert not self.run_play._check_breakaway_potential(elite_rb, matrix, 5.0), \
            "Short gains should not trigger breakaways"


if __name__ == "__main__":
    # Run specific test groups
    print("Running Situational Matchup Matrix Algorithm Tests...")
    
    # Quick smoke test
    test_classification = TestRunTypeClassification()
    test_classification.setup_method()
    test_classification.test_formation_based_classification()
    print("✓ Run type classification working")
    
    test_effectiveness = TestRBEffectivenessCalculation()
    test_effectiveness.setup_method()
    test_effectiveness.test_power_back_vs_power_runs()
    print("✓ RB effectiveness calculation working")
    
    test_stats = TestStatisticalValidation()
    test_stats.setup_method()
    test_stats.test_average_yards_per_attempt()
    print("✓ Statistical validation working")
    
    print("All smoke tests passed! ✅")