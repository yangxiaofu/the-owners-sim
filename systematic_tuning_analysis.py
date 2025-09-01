#!/usr/bin/env python3
"""
Ultra-Think Systematic Tuning Analysis for Pass Play Algorithm

This script performs deep mathematical analysis of the algorithm's behavior to identify
the optimal parameter combinations needed to achieve NFL-realistic statistics.

Mathematical Approach:
1. Analyze each parameter's impact on final outcomes
2. Calculate sensitivity coefficients
3. Identify leverage points for maximum impact
4. Design parameter space exploration
5. Optimize toward NFL targets using systematic adjustment

NFL Targets (2024):
- Completion Rate: 65.3%
- Yards per Attempt: 7.1
- Sack Rate: 6.87%
- Interception Rate: 2.2%
- Touchdown Rate: 4.5%
- Yards per Completion: 10.9
"""

import sys
import os
import random
import statistics
import math
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass
# import numpy as np  # Not needed for this analysis

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.pass_play import PassPlay, ROUTE_CONCEPT_MATRICES, PassGameBalance
from game_engine.field.field_state import FieldState
from game_engine.core.game_orchestrator import SimpleGameEngine


@dataclass
class NFLTargets:
    """2024 NFL target statistics"""
    completion_rate: float = 0.653
    yards_per_attempt: float = 7.1
    sack_rate: float = 0.0687
    interception_rate: float = 0.022
    touchdown_rate: float = 0.045
    yards_per_completion: float = 10.9


@dataclass
class ParameterImpact:
    """Analysis of a parameter's impact on outcomes"""
    parameter_name: str
    current_value: Any
    completion_impact: float
    ypa_impact: float
    td_impact: float
    sack_impact: float
    sensitivity: float  # How much outcomes change per unit parameter change


class SystematicTuningAnalyzer:
    """Ultra-analytical approach to algorithm tuning"""
    
    def __init__(self):
        """Initialize the systematic tuning analyzer"""
        self.nfl_targets = NFLTargets()
        self.engine = SimpleGameEngine()
        self.pass_play = PassPlay()
        self.current_stats = {}
        self.parameter_impacts = {}
        
        print("🧠 ULTRA-THINK SYSTEMATIC TUNING ANALYSIS")
        print("=" * 60)
        print("Mathematical approach to algorithm optimization")
        print("Target: NFL-realistic statistics through parameter optimization")
        print()
    
    def analyze_current_performance(self, sample_size: int = 2000) -> Dict[str, float]:
        """Analyze current algorithm performance with statistical rigor"""
        
        print("📊 CURRENT PERFORMANCE ANALYSIS")
        print("-" * 40)
        print(f"Running {sample_size:,} simulations for baseline measurement...")
        
        outcomes = []
        yards_list = []
        
        for _ in range(sample_size):
            # Create varied test scenarios
            game_state = self._create_random_game_state()
            personnel = self._create_test_personnel()
            
            result = self.pass_play.simulate(personnel, game_state)
            outcomes.append(result.outcome)
            yards_list.append(result.yards_gained)
        
        # Calculate current statistics
        completions = sum(1 for o in outcomes if o in ['gain', 'touchdown'])
        completion_rate = completions / len(outcomes)
        
        sacks = sum(1 for o in outcomes if o == 'sack')
        sack_rate = sacks / len(outcomes)
        
        interceptions = sum(1 for o in outcomes if o == 'interception')
        int_rate = interceptions / len(outcomes)
        
        touchdowns = sum(1 for o in outcomes if o == 'touchdown')
        td_rate = touchdowns / len(outcomes)
        
        ypa = statistics.mean(yards_list)
        
        completion_yards = [y for i, y in enumerate(yards_list) if outcomes[i] in ['gain', 'touchdown']]
        ypc = statistics.mean(completion_yards) if completion_yards else 0
        
        self.current_stats = {
            'completion_rate': completion_rate,
            'yards_per_attempt': ypa,
            'sack_rate': sack_rate,
            'interception_rate': int_rate,
            'touchdown_rate': td_rate,
            'yards_per_completion': ypc
        }
        
        print("Current Performance vs NFL Targets:")
        print(f"  Completion Rate: {completion_rate:.1%} vs {self.nfl_targets.completion_rate:.1%} (gap: {(completion_rate - self.nfl_targets.completion_rate)*100:+.1f}%)")
        print(f"  YPA: {ypa:.1f} vs {self.nfl_targets.yards_per_attempt:.1f} (gap: {ypa - self.nfl_targets.yards_per_attempt:+.1f})")
        print(f"  Sack Rate: {sack_rate:.1%} vs {self.nfl_targets.sack_rate:.1%} (gap: {(sack_rate - self.nfl_targets.sack_rate)*100:+.1f}%)")
        print(f"  INT Rate: {int_rate:.1%} vs {self.nfl_targets.interception_rate:.1%} (gap: {(int_rate - self.nfl_targets.interception_rate)*100:+.1f}%)")
        print(f"  TD Rate: {td_rate:.1%} vs {self.nfl_targets.touchdown_rate:.1%} (gap: {(td_rate - self.nfl_targets.touchdown_rate)*100:+.1f}%)")
        print(f"  YPC: {ypc:.1f} vs {self.nfl_targets.yards_per_completion:.1f} (gap: {ypc - self.nfl_targets.yards_per_completion:+.1f})")
        
        return self.current_stats
    
    def analyze_route_concept_distribution(self, sample_size: int = 1000) -> Dict[str, float]:
        """Analyze how often each route concept is selected"""
        
        print("\n🎯 ROUTE CONCEPT DISTRIBUTION ANALYSIS")
        print("-" * 45)
        
        route_concept_counts = defaultdict(int)
        
        for _ in range(sample_size):
            game_state = self._create_random_game_state()
            personnel = self._create_test_personnel()
            
            route_concept = self.pass_play._determine_route_concept(personnel.formation, game_state)
            route_concept_counts[route_concept] += 1
        
        distribution = {concept: count / sample_size for concept, count in route_concept_counts.items()}
        
        print("Route Concept Usage Distribution:")
        for concept, pct in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            expected_ypa = self._calculate_expected_ypa_for_concept(concept)
            print(f"  {concept:12}: {pct:6.1%} (Expected YPA: {expected_ypa:.1f})")
        
        return distribution
    
    def _calculate_expected_ypa_for_concept(self, concept: str) -> float:
        """Calculate expected YPA for a route concept"""
        matrix = ROUTE_CONCEPT_MATRICES[concept]
        
        # Calculate YAC addition
        yac_multipliers = {
            "quick_game": 0.3, "intermediate": 0.5, "vertical": 0.6, 
            "screens": 0.8, "play_action": 0.4
        }
        yac_potential = yac_multipliers.get(concept, 0.45)
        yac_yards = matrix['base_yards'] * yac_potential * PassGameBalance.YAC_MULTIPLIER
        total_expected_yards = matrix['base_yards'] + yac_yards
        
        # Expected YPA = completion_rate * yards_per_completion
        return matrix['base_completion'] * total_expected_yards
    
    def analyze_mathematical_levers(self) -> Dict[str, ParameterImpact]:
        """Identify the most impactful parameters for tuning"""
        
        print("\n🔬 MATHEMATICAL LEVERAGE ANALYSIS")
        print("-" * 40)
        print("Analyzing parameter sensitivity and impact coefficients...")
        
        # Key parameters to analyze
        parameters_to_test = [
            ('YAC_MULTIPLIER', [0.5, 0.75, 1.0, 1.25]),
            ('BASE_TD_RATE', [0.05, 0.08, 0.12, 0.15]),
            ('TD_MIN_YARDS', [10, 15, 20, 25]),
            ('Quick_Game_Base_Yards', [6, 7, 8, 9]),
            ('Intermediate_Base_Yards', [12, 14, 16, 18]),
            ('Vertical_Base_Yards', [20, 22, 25, 28]),
        ]
        
        impacts = {}
        
        for param_name, test_values in parameters_to_test:
            print(f"\n  Testing {param_name}...")
            
            ypa_impacts = []
            completion_impacts = []
            td_impacts = []
            
            for value in test_values:
                # Temporarily modify parameter
                original_stats = self._test_parameter_value(param_name, value, sample_size=500)
                
                ypa_impact = original_stats['yards_per_attempt'] - self.current_stats.get('yards_per_attempt', 0)
                completion_impact = original_stats['completion_rate'] - self.current_stats.get('completion_rate', 0)
                td_impact = original_stats['touchdown_rate'] - self.current_stats.get('touchdown_rate', 0)
                
                ypa_impacts.append(ypa_impact)
                completion_impacts.append(completion_impact)
                td_impacts.append(td_impact)
            
            # Calculate sensitivity (change in outcome per unit change in parameter)
            if len(test_values) >= 2:
                ypa_sensitivity = abs((ypa_impacts[-1] - ypa_impacts[0]) / (test_values[-1] - test_values[0]))
                completion_sensitivity = abs((completion_impacts[-1] - completion_impacts[0]) / (test_values[-1] - test_values[0]))
                
                overall_sensitivity = ypa_sensitivity + completion_sensitivity
                
                impacts[param_name] = ParameterImpact(
                    parameter_name=param_name,
                    current_value=test_values[0],  # Using first value as baseline
                    completion_impact=max(completion_impacts, key=abs),
                    ypa_impact=max(ypa_impacts, key=abs),
                    td_impact=max(td_impacts, key=abs),
                    sack_impact=0,  # Will be calculated separately if needed
                    sensitivity=overall_sensitivity
                )
                
                print(f"    Max YPA Impact: {max(ypa_impacts, key=abs):+.2f}")
                print(f"    Max Completion Impact: {max(completion_impacts, key=abs):+.1%}")
                print(f"    Sensitivity Score: {overall_sensitivity:.3f}")
        
        # Sort by sensitivity (most impactful first)
        sorted_impacts = sorted(impacts.items(), key=lambda x: x[1].sensitivity, reverse=True)
        
        print("\nPARAMETER IMPACT RANKING (Most to Least Influential):")
        for i, (param_name, impact) in enumerate(sorted_impacts, 1):
            print(f"  {i}. {param_name:20} (Sensitivity: {impact.sensitivity:.3f})")
        
        return impacts
    
    def _test_parameter_value(self, param_name: str, value: Any, sample_size: int = 500) -> Dict[str, float]:
        """Test algorithm performance with a specific parameter value"""
        
        # Store original values
        original_yac = PassGameBalance.YAC_MULTIPLIER
        original_td_rate = PassGameBalance.BASE_TD_RATE
        original_td_min = PassGameBalance.TD_MIN_YARDS
        original_quick = ROUTE_CONCEPT_MATRICES['quick_game']['base_yards']
        original_intermediate = ROUTE_CONCEPT_MATRICES['intermediate']['base_yards']
        original_vertical = ROUTE_CONCEPT_MATRICES['vertical']['base_yards']
        
        # Modify parameter
        if param_name == 'YAC_MULTIPLIER':
            PassGameBalance.YAC_MULTIPLIER = value
        elif param_name == 'BASE_TD_RATE':
            PassGameBalance.BASE_TD_RATE = value
        elif param_name == 'TD_MIN_YARDS':
            PassGameBalance.TD_MIN_YARDS = value
        elif param_name == 'Quick_Game_Base_Yards':
            ROUTE_CONCEPT_MATRICES['quick_game']['base_yards'] = value
        elif param_name == 'Intermediate_Base_Yards':
            ROUTE_CONCEPT_MATRICES['intermediate']['base_yards'] = value
        elif param_name == 'Vertical_Base_Yards':
            ROUTE_CONCEPT_MATRICES['vertical']['base_yards'] = value
        
        # Run test
        outcomes = []
        yards_list = []
        
        for _ in range(sample_size):
            game_state = self._create_random_game_state()
            personnel = self._create_test_personnel()
            
            result = self.pass_play.simulate(personnel, game_state)
            outcomes.append(result.outcome)
            yards_list.append(result.yards_gained)
        
        # Calculate stats
        completions = sum(1 for o in outcomes if o in ['gain', 'touchdown'])
        completion_rate = completions / len(outcomes)
        touchdowns = sum(1 for o in outcomes if o == 'touchdown')
        td_rate = touchdowns / len(outcomes)
        ypa = statistics.mean(yards_list)
        
        # Restore original values
        PassGameBalance.YAC_MULTIPLIER = original_yac
        PassGameBalance.BASE_TD_RATE = original_td_rate
        PassGameBalance.TD_MIN_YARDS = original_td_min
        ROUTE_CONCEPT_MATRICES['quick_game']['base_yards'] = original_quick
        ROUTE_CONCEPT_MATRICES['intermediate']['base_yards'] = original_intermediate
        ROUTE_CONCEPT_MATRICES['vertical']['base_yards'] = original_vertical
        
        return {
            'completion_rate': completion_rate,
            'touchdown_rate': td_rate,
            'yards_per_attempt': ypa
        }
    
    def generate_optimal_parameter_set(self) -> Dict[str, Any]:
        """Generate mathematically optimized parameter set"""
        
        print("\n🎯 OPTIMAL PARAMETER CALCULATION")
        print("-" * 35)
        
        # Current gaps from NFL targets
        completion_gap = self.nfl_targets.completion_rate - self.current_stats['completion_rate']
        ypa_gap = self.nfl_targets.yards_per_attempt - self.current_stats['yards_per_attempt']
        td_gap = self.nfl_targets.touchdown_rate - self.current_stats['touchdown_rate']
        ypc_gap = self.nfl_targets.yards_per_completion - self.current_stats['yards_per_completion']
        
        print(f"Gaps to close:")
        print(f"  Completion: {completion_gap:+.1%}")
        print(f"  YPA: {ypa_gap:+.1f}")
        print(f"  TD Rate: {td_gap:+.1%}")
        print(f"  YPC: {ypc_gap:+.1f}")
        
        # Mathematical optimization approach
        optimal_params = {}
        
        # YAC Multiplier optimization (biggest impact on YPA and YPC)
        # Target: Increase YPC from ~7 to 10.9 (55% increase)
        # Current YAC multiplier: 0.75, need ~40% more yards
        optimal_yac = 0.75 * (1 + ypc_gap / self.current_stats['yards_per_completion'])
        optimal_params['YAC_MULTIPLIER'] = min(1.2, max(0.8, optimal_yac))
        
        # TD Rate optimization 
        # Current TD rate too low, need to increase BASE_TD_RATE and lower TD_MIN_YARDS
        td_multiplier = self.nfl_targets.touchdown_rate / max(0.001, self.current_stats['touchdown_rate'])
        optimal_td_rate = PassGameBalance.BASE_TD_RATE * min(3.0, td_multiplier)
        optimal_params['BASE_TD_RATE'] = min(0.15, max(0.08, optimal_td_rate))
        optimal_params['TD_MIN_YARDS'] = max(8, int(15 - ypc_gap))  # Lower threshold if YPC is low
        
        # Base yards optimization (route concepts)
        # Increase all base yards proportionally to close YPA gap
        yards_multiplier = 1 + (ypa_gap / self.current_stats['yards_per_attempt']) * 0.5
        optimal_params['Quick_Game_Base_Yards'] = ROUTE_CONCEPT_MATRICES['quick_game']['base_yards'] * yards_multiplier
        optimal_params['Intermediate_Base_Yards'] = ROUTE_CONCEPT_MATRICES['intermediate']['base_yards'] * yards_multiplier
        optimal_params['Vertical_Base_Yards'] = ROUTE_CONCEPT_MATRICES['vertical']['base_yards'] * yards_multiplier
        
        print(f"\nOptimal Parameters (Mathematically Derived):")
        for param, value in optimal_params.items():
            print(f"  {param:25}: {value:.3f}")
        
        return optimal_params
    
    def _create_random_game_state(self) -> FieldState:
        """Create randomized game state for testing"""
        field_state = FieldState()
        field_state.down = random.randint(1, 3)
        field_state.yards_to_go = random.randint(1, 15)
        field_state.field_position = random.randint(10, 90)
        return field_state
    
    def _create_test_personnel(self):
        """Create test personnel package"""
        from unittest.mock import Mock
        personnel = Mock()
        personnel.formation = random.choice(["shotgun", "shotgun_spread", "I_formation", "singleback", "pistol"])
        personnel.defensive_call = random.choice(["zone_coverage", "man_coverage", "blitz"])
        
        # Create QB with realistic ratings
        personnel.qb_on_field = Mock()
        personnel.qb_on_field.accuracy = random.randint(60, 90)
        personnel.qb_on_field.release_time = random.randint(60, 90)
        personnel.qb_on_field.mobility = random.randint(40, 80)
        personnel.qb_on_field.arm_strength = random.randint(60, 90)
        personnel.qb_on_field.decision_making = random.randint(60, 90)
        personnel.qb_on_field.play_action = random.randint(60, 90)
        
        # Create WR
        personnel.primary_wr = Mock()
        personnel.primary_wr.route_running = random.randint(60, 90)
        personnel.primary_wr.hands = random.randint(60, 90)
        personnel.primary_wr.speed = random.randint(60, 90)
        personnel.primary_wr.vision = random.randint(60, 90)
        
        # Create RB and TE
        personnel.rb_on_field = Mock()
        personnel.rb_on_field.pass_protection = random.randint(40, 70)
        personnel.te_on_field = Mock()
        personnel.te_on_field.pass_protection = random.randint(50, 80)
        
        return personnel
    
    def run_complete_analysis(self):
        """Run the complete systematic tuning analysis"""
        
        print("🚀 EXECUTING ULTRA-THINK SYSTEMATIC ANALYSIS")
        print("=" * 60)
        
        # Step 1: Current performance analysis
        self.analyze_current_performance(sample_size=3000)
        
        # Step 2: Route concept distribution analysis
        route_distribution = self.analyze_route_concept_distribution(sample_size=1500)
        
        # Step 3: Parameter impact analysis
        parameter_impacts = self.analyze_mathematical_levers()
        
        # Step 4: Generate optimal parameters
        optimal_params = self.generate_optimal_parameter_set()
        
        # Step 5: Final recommendations
        print("\n" + "=" * 60)
        print("🎯 SYSTEMATIC TUNING RECOMMENDATIONS")
        print("=" * 60)
        
        print("\n1. HIGHEST PRIORITY ADJUSTMENTS:")
        print("   Based on mathematical sensitivity analysis:")
        
        top_3_params = sorted(parameter_impacts.items(), key=lambda x: x[1].sensitivity, reverse=True)[:3]
        for i, (param, impact) in enumerate(top_3_params, 1):
            recommended_value = optimal_params.get(param, "No recommendation")
            print(f"   {i}. {param}: {recommended_value} (Sensitivity: {impact.sensitivity:.3f})")
        
        print("\n2. ALGORITHMIC INSIGHTS:")
        print("   - Route concepts with highest expected YPA should be used more frequently")
        print("   - YAC multiplier has massive impact on both YPA and YPC")
        print("   - TD threshold too high relative to actual completion yards")
        print("   - Base yards need proportional increase across all concepts")
        
        print("\n3. IMPLEMENTATION STRATEGY:")
        print("   - Apply highest-sensitivity parameters first")
        print("   - Test each change individually before combining")
        print("   - Use benchmarking suite to validate each adjustment")
        print("   - Iterate until all NFL targets are within 5% tolerance")
        
        return {
            'current_stats': self.current_stats,
            'route_distribution': route_distribution,
            'parameter_impacts': parameter_impacts,
            'optimal_params': optimal_params
        }


def main():
    """Execute the ultra-think systematic tuning analysis"""
    
    random.seed(42)  # Reproducible analysis
    
    analyzer = SystematicTuningAnalyzer()
    results = analyzer.run_complete_analysis()
    
    print("\n" + "=" * 60)
    print("🧠 ULTRA-THINK ANALYSIS COMPLETE")
    print("=" * 60)
    print("Results exported for implementation guidance.")
    
    return results


if __name__ == "__main__":
    main()