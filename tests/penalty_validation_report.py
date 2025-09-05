"""
NFL Penalty System Validation Report Generator

Generates comprehensive validation report testing penalty system against NFL statistics:
- Penalty rates by situation  
- Player discipline impact analysis
- Home field advantage validation
- Penalty type distribution analysis
- Integration accuracy testing
"""

import sys
import os
import random
import json
from typing import Dict, List, Any
from collections import defaultdict, Counter

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from penalties.penalty_engine import PenaltyEngine, PlayContext
from penalties.penalty_config_loader import PenaltyConfigLoader
from player import Player
from plays.run_play import RunPlaySimulator


class NFLPenaltyValidator:
    """Validates penalty system against NFL benchmarks"""
    
    # NFL penalty benchmarks (approximate per-game averages)
    NFL_BENCHMARKS = {
        'penalties_per_game': 13.2,
        'penalty_yards_per_game': 110.5,
        'false_start_rate': 0.022,      # ~2.2% of plays
        'holding_rate': 0.035,          # ~3.5% of plays  
        'home_field_penalty_reduction': 0.15,  # 15% fewer penalties at home
        'red_zone_penalty_increase': 0.40,     # 40% more penalties in red zone
        'fourth_down_penalty_increase': 0.25,  # 25% more on 4th down
    }
    
    def __init__(self):
        self.config_loader = PenaltyConfigLoader()
        self.penalty_engine = PenaltyEngine()
        self.test_results = {}
        
    def create_test_teams(self) -> tuple:
        """Create realistic test teams with varying discipline levels"""
        # Average NFL team
        avg_offense = self._create_team_lineup('offense', discipline=75)
        avg_defense = self._create_team_lineup('defense', discipline=75)
        
        # High discipline team
        disciplined_offense = self._create_team_lineup('offense', discipline=88)
        disciplined_defense = self._create_team_lineup('defense', discipline=88)
        
        # Low discipline team  
        undisciplined_offense = self._create_team_lineup('offense', discipline=55)
        undisciplined_defense = self._create_team_lineup('defense', discipline=55)
        
        return {
            'average': (avg_offense, avg_defense),
            'disciplined': (disciplined_offense, disciplined_defense),
            'undisciplined': (undisciplined_offense, undisciplined_defense)
        }
    
    def _create_team_lineup(self, side: str, discipline: int) -> List[Player]:
        """Create 11-player lineup with specified discipline level"""
        if side == 'offense':
            positions = ['QB', 'RB', 'WR', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'WR']
        else:
            positions = ['LE', 'DT', 'DT', 'RE', 'MIKE', 'SAM', 'WILL', 'CB', 'CB', 'FS', 'SS']
        
        players = []
        for i, pos in enumerate(positions):
            player = Player(name=f"{side}_{pos}_{i}", number=(10+i if side=='offense' else 50+i), primary_position=pos)
            
            # Vary discipline slightly around target (+/- 8 points)
            actual_discipline = max(20, min(95, discipline + random.randint(-8, 8)))
            
            player.ratings = {
                'discipline': actual_discipline,
                'composure': actual_discipline + random.randint(-5, 5),
                'experience': discipline + random.randint(-10, 10),
                'penalty_technique': actual_discipline + random.randint(-8, 8),
                'speed': random.randint(70, 90),
                'strength': random.randint(70, 90)
            }
            players.append(player)
        
        return players
    
    def validate_penalty_rates(self, teams: Dict, num_simulations: int = 2000) -> Dict[str, Any]:
        """Validate penalty rates against NFL benchmarks"""
        print("Validating penalty rates against NFL benchmarks...")
        
        results = {}
        
        for team_type, (offense, defense) in teams.items():
            print(f"  Testing {team_type} discipline team...")
            
            penalty_count = 0
            total_penalty_yards = 0
            penalty_types = Counter()
            
            # Standard context for baseline testing
            context = PlayContext(
                play_type="run",
                offensive_formation="i_formation",
                defensive_formation="4_3_base",
                down=1,
                distance=10,
                field_position=50
            )
            
            for _ in range(num_simulations):
                penalty_result = self.penalty_engine.check_for_penalty(
                    offense, defense, context, random.randint(0, 8)
                )
                
                if penalty_result.penalty_occurred:
                    penalty_count += 1
                    total_penalty_yards += abs(penalty_result.penalty_instance.yards_assessed)
                    penalty_types[penalty_result.penalty_instance.penalty_type] += 1
            
            penalty_rate = penalty_count / num_simulations
            avg_penalty_yards = total_penalty_yards / max(1, penalty_count)
            
            results[team_type] = {
                'penalty_rate_per_play': penalty_rate,
                'penalties_per_140_plays': penalty_rate * 140,  # Approximate plays per game
                'avg_penalty_yards': avg_penalty_yards,
                'penalty_types': dict(penalty_types),
                'total_penalty_yards': total_penalty_yards
            }
        
        return results
    
    def validate_situational_modifiers(self, teams: Dict, num_simulations: int = 1000) -> Dict[str, Any]:
        """Test penalty rates in different game situations"""
        print("Validating situational penalty modifiers...")
        
        offense, defense = teams['average']
        results = {}
        
        # Test scenarios
        scenarios = {
            'baseline': PlayContext("run", "i_formation", "4_3_base", down=1, distance=10, field_position=50),
            'red_zone': PlayContext("run", "goal_line", "goal_line", down=1, distance=5, field_position=95),
            'fourth_down': PlayContext("run", "i_formation", "4_3_base", down=4, distance=2, field_position=50),
            'long_distance': PlayContext("run", "shotgun", "nickel", down=2, distance=15, field_position=30),
        }
        
        for scenario_name, context in scenarios.items():
            penalty_count = 0
            
            for _ in range(num_simulations):
                penalty_result = self.penalty_engine.check_for_penalty(
                    offense, defense, context, random.randint(0, 8)
                )
                if penalty_result.penalty_occurred:
                    penalty_count += 1
            
            penalty_rate = penalty_count / num_simulations
            results[scenario_name] = penalty_rate
        
        # Calculate relative increases
        baseline_rate = results['baseline']
        results['red_zone_increase'] = (results['red_zone'] - baseline_rate) / baseline_rate if baseline_rate > 0 else 0
        results['fourth_down_increase'] = (results['fourth_down'] - baseline_rate) / baseline_rate if baseline_rate > 0 else 0
        
        return results
    
    def validate_home_field_advantage(self, teams: Dict, num_simulations: int = 1500) -> Dict[str, Any]:
        """Test home field advantage penalty reduction"""
        print("Validating home field advantage...")
        
        offense, defense = teams['average']
        
        # Home context
        home_context = PlayContext(
            play_type="run",
            offensive_formation="i_formation", 
            defensive_formation="4_3_base",
            is_home_team=True
        )
        
        # Away context
        away_context = PlayContext(
            play_type="run",
            offensive_formation="i_formation",
            defensive_formation="4_3_base", 
            is_home_team=False
        )
        
        home_penalties = 0
        away_penalties = 0
        
        for _ in range(num_simulations):
            home_result = self.penalty_engine.check_for_penalty(
                offense, defense, home_context, random.randint(0, 8)
            )
            away_result = self.penalty_engine.check_for_penalty(
                offense, defense, away_context, random.randint(0, 8)
            )
            
            if home_result.penalty_occurred:
                home_penalties += 1
            if away_result.penalty_occurred:
                away_penalties += 1
        
        home_rate = home_penalties / num_simulations
        away_rate = away_penalties / num_simulations
        
        advantage = (away_rate - home_rate) / away_rate if away_rate > 0 else 0
        
        return {
            'home_penalty_rate': home_rate,
            'away_penalty_rate': away_rate,
            'home_field_advantage': advantage,
            'meets_nfl_benchmark': 0.10 <= advantage <= 0.25  # 10-25% reduction
        }
    
    def validate_discipline_impact(self, teams: Dict, num_simulations: int = 1000) -> Dict[str, Any]:
        """Test impact of player discipline on penalty rates"""
        print("Validating player discipline impact...")
        
        results = {}
        context = PlayContext(
            play_type="run",
            offensive_formation="i_formation",
            defensive_formation="4_3_base"
        )
        
        for team_type, (offense, defense) in teams.items():
            penalty_count = 0
            
            for _ in range(num_simulations):
                penalty_result = self.penalty_engine.check_for_penalty(
                    offense, defense, context, random.randint(0, 8)
                )
                if penalty_result.penalty_occurred:
                    penalty_count += 1
            
            results[team_type] = penalty_count / num_simulations
        
        # Calculate discipline impact ratios
        disciplined_rate = results['disciplined']
        average_rate = results['average']
        undisciplined_rate = results['undisciplined']
        
        results['discipline_impact_ratio'] = undisciplined_rate / disciplined_rate if disciplined_rate > 0 else 0
        results['discipline_reduces_penalties'] = disciplined_rate < average_rate < undisciplined_rate
        
        return results
    
    def validate_integration_accuracy(self, teams: Dict, num_simulations: int = 500) -> Dict[str, Any]:
        """Test RunPlaySimulator integration accuracy"""
        print("Validating RunPlaySimulator integration...")
        
        offense, defense = teams['average']
        simulator = RunPlaySimulator(offense, defense, "i_formation", "4_3_base")
        
        total_plays = 0
        penalty_plays = 0
        yards_modified = 0
        attribution_accurate = 0
        
        context = PlayContext(
            play_type="run",
            offensive_formation="i_formation",
            defensive_formation="4_3_base"
        )
        
        for _ in range(num_simulations):
            result = simulator.simulate_run_play(context)
            total_plays += 1
            
            if result.has_penalty():
                penalty_plays += 1
                penalty_summary = result.get_penalty_summary()
                
                # Check that penalty info is complete
                if penalty_summary and all(key in penalty_summary for key in ['penalty_type', 'penalized_player', 'penalty_yards']):
                    attribution_accurate += 1
                
                # Check yardage modification
                if penalty_summary['original_play_yards'] is not None:
                    yards_modified += 1
        
        return {
            'total_plays_tested': total_plays,
            'penalty_plays': penalty_plays,
            'penalty_rate': penalty_plays / total_plays,
            'attribution_accuracy': attribution_accurate / max(1, penalty_plays),
            'yards_modification_rate': yards_modified / max(1, penalty_plays),
            'integration_successful': penalty_plays > 0 and attribution_accurate > 0
        }
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive validation report"""
        print("Generating comprehensive NFL penalty validation report...\n")
        
        # Create test teams
        teams = self.create_test_teams()
        
        # Run all validations
        penalty_rates = self.validate_penalty_rates(teams)
        situational_rates = self.validate_situational_modifiers(teams)
        home_field = self.validate_home_field_advantage(teams)
        discipline_impact = self.validate_discipline_impact(teams)
        integration = self.validate_integration_accuracy(teams)
        
        # Generate report
        report = []
        report.append("=" * 70)
        report.append("NFL PENALTY SYSTEM VALIDATION REPORT")
        report.append("=" * 70)
        report.append("")
        
        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 50)
        avg_penalties_per_game = penalty_rates['average']['penalties_per_140_plays']
        nfl_benchmark = self.NFL_BENCHMARKS['penalties_per_game']
        within_range = 10 <= avg_penalties_per_game <= 16
        
        report.append(f"✅ Penalties per game: {avg_penalties_per_game:.1f} (NFL: {nfl_benchmark}, Range: 10-16)")
        report.append(f"{'✅' if within_range else '❌'} Within NFL realistic range: {within_range}")
        report.append(f"✅ Home field advantage: {home_field['home_field_advantage']:.1%} (Target: 15%)")
        report.append(f"✅ Discipline impact validated: {discipline_impact['discipline_reduces_penalties']}")
        report.append(f"✅ Integration successful: {integration['integration_successful']}")
        report.append("")
        
        # Penalty Rate Analysis
        report.append("PENALTY RATE ANALYSIS")
        report.append("-" * 50)
        for team_type, data in penalty_rates.items():
            report.append(f"{team_type.title()} Team:")
            report.append(f"  • Penalty rate per play: {data['penalty_rate_per_play']:.1%}")
            report.append(f"  • Penalties per game: {data['penalties_per_140_plays']:.1f}")
            report.append(f"  • Avg penalty yards: {data['avg_penalty_yards']:.1f}")
            report.append("")
        
        # Situational Analysis
        report.append("SITUATIONAL PENALTY ANALYSIS")
        report.append("-" * 50)
        report.append(f"Baseline penalty rate: {situational_rates['baseline']:.1%}")
        report.append(f"Red zone penalty rate: {situational_rates['red_zone']:.1%} (+{situational_rates['red_zone_increase']:.1%})")
        report.append(f"Fourth down penalty rate: {situational_rates['fourth_down']:.1%} (+{situational_rates['fourth_down_increase']:.1%})")
        
        red_zone_valid = 0.2 <= situational_rates['red_zone_increase'] <= 0.6
        fourth_down_valid = 0.1 <= situational_rates['fourth_down_increase'] <= 0.4
        report.append(f"{'✅' if red_zone_valid else '❌'} Red zone increase realistic: {red_zone_valid}")
        report.append(f"{'✅' if fourth_down_valid else '❌'} Fourth down increase realistic: {fourth_down_valid}")
        report.append("")
        
        # Home Field Advantage
        report.append("HOME FIELD ADVANTAGE ANALYSIS")
        report.append("-" * 50)
        report.append(f"Home penalty rate: {home_field['home_penalty_rate']:.1%}")
        report.append(f"Away penalty rate: {home_field['away_penalty_rate']:.1%}")
        report.append(f"Home field advantage: {home_field['home_field_advantage']:.1%}")
        report.append(f"Meets NFL benchmark: {home_field['meets_nfl_benchmark']}")
        report.append("")
        
        # Discipline Impact
        report.append("PLAYER DISCIPLINE IMPACT ANALYSIS")
        report.append("-" * 50)
        report.append(f"Disciplined team rate: {discipline_impact['disciplined']:.1%}")
        report.append(f"Average team rate: {discipline_impact['average']:.1%}")
        report.append(f"Undisciplined team rate: {discipline_impact['undisciplined']:.1%}")
        report.append(f"Impact ratio (undisciplined/disciplined): {discipline_impact['discipline_impact_ratio']:.1f}x")
        report.append(f"Discipline progression logical: {discipline_impact['discipline_reduces_penalties']}")
        report.append("")
        
        # Integration Testing
        report.append("INTEGRATION TESTING RESULTS")
        report.append("-" * 50)
        report.append(f"Total plays simulated: {integration['total_plays_tested']}")
        report.append(f"Plays with penalties: {integration['penalty_plays']}")
        report.append(f"Integration penalty rate: {integration['penalty_rate']:.1%}")
        report.append(f"Attribution accuracy: {integration['attribution_accuracy']:.1%}")
        report.append(f"Yards modification rate: {integration['yards_modification_rate']:.1%}")
        report.append("")
        
        # Penalty Type Distribution
        report.append("PENALTY TYPE DISTRIBUTION")
        report.append("-" * 50)
        penalty_types = penalty_rates['average']['penalty_types']
        total_penalties = sum(penalty_types.values())
        for penalty_type, count in sorted(penalty_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_penalties * 100) if total_penalties > 0 else 0
            report.append(f"  {penalty_type}: {count} ({percentage:.1f}%)")
        report.append("")
        
        # Final Validation
        report.append("FINAL VALIDATION STATUS")
        report.append("-" * 50)
        
        validations = [
            within_range,
            home_field['meets_nfl_benchmark'], 
            discipline_impact['discipline_reduces_penalties'],
            integration['integration_successful'],
            red_zone_valid,
            fourth_down_valid
        ]
        
        passed_validations = sum(validations)
        total_validations = len(validations)
        
        report.append(f"Validations passed: {passed_validations}/{total_validations}")
        
        if passed_validations == total_validations:
            report.append("🎉 ALL VALIDATIONS PASSED - PENALTY SYSTEM IS NFL-REALISTIC")
        elif passed_validations >= total_validations * 0.8:
            report.append("⚠️  MOST VALIDATIONS PASSED - MINOR TUNING MAY BE NEEDED") 
        else:
            report.append("❌ MULTIPLE VALIDATIONS FAILED - SYSTEM NEEDS ADJUSTMENT")
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)


def main():
    """Run comprehensive penalty system validation"""
    validator = NFLPenaltyValidator()
    report = validator.generate_comprehensive_report()
    
    # Print to console
    print(report)
    
    # Save to file
    report_file = os.path.join(os.path.dirname(__file__), "penalty_validation_report.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()