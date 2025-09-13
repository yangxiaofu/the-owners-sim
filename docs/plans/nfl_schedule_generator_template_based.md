# NFL Template-Based Schedule Generator Plan

## Executive Summary

This document outlines a sophisticated template-based approach for generating NFL season schedules that are compatible with the CalendarManager system. The generator uses actual NFL scheduling patterns as templates, intelligently maps teams to slots while preserving structural integrity, and outputs JSON formatted schedules ready for simulation.

## 1. Overview

### 1.1 Purpose
Generate realistic, rule-compliant NFL season schedules that:
- Follow all NFL scheduling rules and constraints
- Preserve traditional rivalries and special games
- Balance competitive fairness
- Integrate seamlessly with CalendarManager

### 1.2 Why Template-Based Approach

**Advantages:**
- **Realism**: Produces schedules that match actual NFL patterns
- **Complexity Management**: NFL rules are encoded in the template
- **Flexibility**: Easy to modify for different scenarios
- **Validation**: Built-in structure ensures valid outputs
- **Historical Accuracy**: Can use actual past schedules as templates

**Comparison to Other Approaches:**
- Simple Round-Robin: Lacks NFL's complex rules
- Division-Based: Difficult to balance all constraints
- Template-Based: Best of both worlds - structure with flexibility

## 2. Template Structure Design

### 2.1 Core Template Schema

```json
{
  "template_metadata": {
    "source_year": 2023,
    "template_version": "1.0",
    "template_type": "full_season",
    "total_slots": 272,
    "weeks": 18,
    "special_events": {
      "thanksgiving": {"week": 12, "games": 3},
      "christmas": {"week": 16, "games": 2},
      "international": {"total": 5, "weeks": [4, 5, 7, 10, 11]}
    },
    "primetime_distribution": {
      "thursday_night": 15,
      "sunday_night": 18,
      "monday_night": 17
    }
  },
  "schedule_slots": [...],
  "matchup_patterns": {...},
  "rotation_rules": {...}
}
```

### 2.2 Schedule Slot Definition

Each game slot in the template contains:

```json
{
  "slot_id": "W01_SUN_CBS_01",
  "week": 1,
  "date_offset": 3,  // Days from week start
  "time": "13:00",
  "time_zone": "ET",
  "slot_attributes": {
    "type": "standard",
    "network": "CBS",
    "broadcast_type": "regional",
    "importance": "normal"
  },
  "matchup_requirements": {
    "type": "divisional",
    "conference": "same",
    "rivalry_tier": "any",
    "market_size": "any"
  },
  "template_matchup": {
    "home": {"division": "AFC_North", "standing": 1},
    "away": {"division": "AFC_North", "standing": 3}
  }
}
```

### 2.3 Special Slot Types

```python
SLOT_TYPES = {
    "season_opener": {
        "count": 1,
        "requirements": ["super_bowl_winner_home", "high_profile_matchup"]
    },
    "thanksgiving": {
        "count": 3,
        "fixed_hosts": [11, 9],  # Lions, Cowboys
        "requirements": ["traditional_game", "national_appeal"]
    },
    "christmas": {
        "count": 1-3,
        "requirements": ["flexible_date", "primetime_worthy"]
    },
    "international": {
        "count": 5,
        "requirements": ["travel_capable", "marketing_value"]
    },
    "primetime": {
        "count": 50,
        "requirements": ["competitive_teams", "storyline"]
    },
    "divisional_finale": {
        "count": 16,
        "requirements": ["week_18", "playoff_implications"]
    }
}
```

## 3. Core Components

### 3.1 TeamClassifier

Classifies teams based on multiple criteria for intelligent slot assignment:

```python
class TeamClassifier:
    def __init__(self, season_year):
        self.year = season_year
        self.team_data = self.load_team_data()
        self.previous_standings = self.load_previous_standings()
    
    def classify_teams(self):
        return {
            "market_tiers": self._calculate_market_tiers(),
            "competitive_tiers": self._calculate_competitive_tiers(),
            "rivalry_groups": self._identify_rivalry_groups(),
            "special_designations": self._identify_special_teams(),
            "scheduling_priorities": self._calculate_priorities()
        }
    
    def _calculate_market_tiers(self):
        """Classify teams by market size and national appeal"""
        return {
            "tier_1_national": [9, 22, 12, 28, 16],  # Cowboys, Patriots, Packers, 49ers, Chiefs
            "tier_2_large": [24, 25, 6, 26, 19, 11],  # Giants, Jets, Bears, Eagles, Rams, Lions
            "tier_3_medium": [...],
            "tier_4_small": [...]
        }
    
    def _calculate_competitive_tiers(self):
        """Based on previous season performance"""
        return {
            "super_bowl_contenders": self.previous_standings["playoff_teams"][:8],
            "playoff_bubble": self.previous_standings["ranked"][9:20],
            "rebuilding": self.previous_standings["ranked"][21:32]
        }
    
    def _identify_rivalry_groups(self):
        """Historic and division rivalries"""
        return [
            {"teams": [12, 6], "weight": 10, "name": "Packers-Bears"},
            {"teams": [9, 32], "weight": 9, "name": "Cowboys-Commanders"},
            {"teams": [27, 3], "weight": 9, "name": "Steelers-Ravens"},
            {"teams": [22, 25], "weight": 8, "name": "Patriots-Jets"},
            # ... more rivalries
        ]
```

### 3.2 ScheduleConstraintSolver

Constraint satisfaction problem solver for slot assignment:

```python
class ScheduleConstraintSolver:
    def __init__(self):
        self.constraints = self._define_constraints()
        self.optimizer = ConstraintOptimizer()
    
    def _define_constraints(self):
        return {
            "hard": [
                HardConstraint("each_team_plays_17_games"),
                HardConstraint("no_duplicate_matchups_except_division"),
                HardConstraint("division_opponents_twice_home_away"),
                HardConstraint("bye_week_between_4_and_12"),
                HardConstraint("no_team_plays_same_week_twice")
            ],
            "soft": [
                SoftConstraint("minimize_consecutive_road_games", weight=5),
                SoftConstraint("spread_division_games", weight=4),
                SoftConstraint("primetime_equity", weight=3),
                SoftConstraint("travel_distance_fairness", weight=2),
                SoftConstraint("competitive_balance", weight=2)
            ]
        }
    
    def solve(self, template_slots, team_classifications, rotation_rules):
        """
        Main solving algorithm using constraint satisfaction
        """
        # Initialize solution space
        solution = ScheduleSolution(template_slots)
        
        # Phase 1: Assign fixed games (Thanksgiving, etc.)
        solution = self._assign_fixed_games(solution)
        
        # Phase 2: Assign division games
        solution = self._assign_division_games(solution, rotation_rules)
        
        # Phase 3: Assign conference games
        solution = self._assign_conference_games(solution, rotation_rules)
        
        # Phase 4: Assign inter-conference games
        solution = self._assign_interconference_games(solution, rotation_rules)
        
        # Phase 5: Optimize using simulated annealing
        solution = self.optimizer.optimize(solution, self.constraints)
        
        return solution
```

### 3.3 TemplateRotationEngine

Handles year-to-year rotation patterns:

```python
class TemplateRotationEngine:
    """
    Implements NFL's rotation system:
    - Division matchups: Every team plays division opponents twice
    - Conference rotation: Play one division every 3 years
    - Inter-conference: Play one division every 4 years
    - Place-based: Play same-place finishers
    """
    
    def __init__(self, base_year, target_year):
        self.base_year = base_year
        self.target_year = target_year
        self.rotation_offset = target_year - base_year
    
    def generate_matchup_requirements(self):
        matchups = {
            "division": self._generate_division_matchups(),
            "conference": self._generate_conference_matchups(),
            "interconference": self._generate_interconference_matchups(),
            "place_based": self._generate_place_based_matchups()
        }
        return matchups
    
    def _generate_conference_matchups(self):
        """
        Conference rotation on 3-year cycle
        """
        rotations = {
            0: {"AFC_East": "AFC_North", "AFC_North": "AFC_West", ...},
            1: {"AFC_East": "AFC_South", "AFC_North": "AFC_East", ...},
            2: {"AFC_East": "AFC_West", "AFC_North": "AFC_South", ...}
        }
        cycle_position = self.rotation_offset % 3
        return rotations[cycle_position]
    
    def _generate_interconference_matchups(self):
        """
        Inter-conference rotation on 4-year cycle
        """
        rotations = {
            0: {"AFC_East": "NFC_North", "AFC_North": "NFC_West", ...},
            1: {"AFC_East": "NFC_South", "AFC_North": "NFC_North", ...},
            2: {"AFC_East": "NFC_East", "AFC_North": "NFC_South", ...},
            3: {"AFC_East": "NFC_West", "AFC_North": "NFC_East", ...}
        }
        cycle_position = self.rotation_offset % 4
        return rotations[cycle_position]
```

### 3.4 NFLScheduleBuilder

Main orchestrator class:

```python
class NFLScheduleBuilder:
    def __init__(self, template_path, year, options=None):
        self.template = self.load_template(template_path)
        self.year = year
        self.options = options or default_options()
        self.classifier = TeamClassifier(year)
        self.rotation_engine = TemplateRotationEngine(
            self.template['template_metadata']['source_year'],
            year
        )
        self.solver = ScheduleConstraintSolver()
        self.validator = ScheduleValidator()
    
    def generate_schedule(self):
        """
        Main generation pipeline
        """
        # Step 1: Classification
        team_data = self.classifier.classify_teams()
        
        # Step 2: Generate matchup requirements
        matchup_requirements = self.rotation_engine.generate_matchup_requirements()
        
        # Step 3: Solve constraint problem
        solution = self.solver.solve(
            self.template['schedule_slots'],
            team_data,
            matchup_requirements
        )
        
        # Step 4: Apply special games
        solution = self._apply_special_games(solution)
        
        # Step 5: Validate
        validation_result = self.validator.validate(solution)
        if not validation_result.is_valid:
            solution = self._fix_validation_errors(solution, validation_result.errors)
        
        # Step 6: Convert to output format
        schedule_json = self._convert_to_json(solution)
        
        return schedule_json
    
    def _apply_special_games(self, solution):
        """Apply Thanksgiving, Christmas, International games"""
        # Thanksgiving
        solution = self._apply_thanksgiving_games(solution)
        
        # International Series
        solution = self._apply_international_games(solution)
        
        # Flex scheduling for late season
        if self.options['enable_flex_scheduling']:
            solution = self._apply_flex_scheduling(solution)
        
        return solution
```

## 4. NFL Scheduling Rules

### 4.1 Required Matchups (17 Games per Team)

Each team must play exactly:
- **6 games** vs division opponents (3 rivals × 2 games each)
- **4 games** vs another division in same conference
- **4 games** vs a division in other conference  
- **2 games** vs same-place finishers in conference (different divisions)
- **1 game** vs same-place finisher in other conference

### 4.2 Home/Away Balance

- Each team plays either 8 home + 9 away OR 9 home + 8 away
- Alternates year-to-year for fairness
- Division games split 1 home, 1 away with each opponent

### 4.3 Scheduling Windows

```python
SCHEDULING_WINDOWS = {
    "preseason": {"weeks": [0, -1, -2, -3], "games_per_team": 3},
    "regular_season": {
        "weeks": 18,
        "bye_weeks": {"earliest": 4, "latest": 12},
        "thursday_games": {"start_week": 2, "thanksgiving": 12},
        "saturday_games": {"weeks": [15, 16, 17]},
        "flex_scheduling": {"start_week": 11, "end_week": 17}
    },
    "playoffs": {
        "wild_card": {"teams": 14, "games": 6},
        "divisional": {"teams": 8, "games": 4},
        "championship": {"teams": 4, "games": 2},
        "super_bowl": {"teams": 2, "games": 1}
    }
}
```

## 5. Output Format

### 5.1 Schedule JSON Structure

```json
{
  "season_metadata": {
    "year": 2024,
    "type": "regular_season",
    "total_weeks": 18,
    "total_games": 272,
    "generation_timestamp": "2024-01-15T10:30:00Z",
    "generator_version": "1.0",
    "template_source": "nfl_2023_actual.json"
  },
  "games": [
    {
      "game_id": "2024_01_001",
      "week": 1,
      "date": "2024-09-05",
      "time": "20:20",
      "time_zone": "ET",
      "away_team_id": 11,
      "home_team_id": 16,
      "away_team_abbr": "DET",
      "home_team_abbr": "KC",
      "stadium": "Arrowhead Stadium",
      "network": "NBC",
      "time_slot_type": "TNF",
      "game_attributes": {
        "is_divisional": false,
        "is_conference": true,
        "is_primetime": true,
        "is_international": false,
        "special_designation": "season_opener"
      }
    }
  ],
  "bye_weeks": {
    "5": [1, 11, 19, 23],
    "6": [2, 8, 14, 20],
    "7": [3, 9, 15, 21],
    "9": [4, 10, 16, 22],
    "10": [5, 12, 17, 24],
    "11": [6, 13, 18, 25],
    "12": [7, 26, 27, 28],
    "14": [29, 30, 31, 32]
  }
}
```

### 5.2 CalendarManager Integration Format

```python
def convert_to_calendar_events(schedule_json):
    """Convert schedule JSON to CalendarManager events"""
    events = []
    
    for game in schedule_json['games']:
        event = GameSimulationEvent(
            date=datetime.strptime(
                f"{game['date']} {game['time']}", 
                "%Y-%m-%d %H:%M"
            ),
            away_team_id=game['away_team_id'],
            home_team_id=game['home_team_id'],
            week=game['week'],
            season_type="regular_season",
            overtime_type="regular_season"
        )
        events.append(event)
    
    return events
```

## 6. Validation System

### 6.1 Validation Rules

```python
class ScheduleValidator:
    def __init__(self):
        self.rules = [
            GameCountRule(),           # Each team plays 17 games
            HomeAwayBalanceRule(),      # 8-9 or 9-8 split
            DivisionMatchupRule(),      # Each division opponent twice
            NoConflictRule(),           # No team plays twice in same week
            ByeWeekRule(),             # Bye between weeks 4-12
            ConsecutiveGameRule(),      # Max 3 consecutive home/away
            PrimetimeEquityRule(),      # Fair primetime distribution
            TravelFairnessRule()        # Reasonable travel requirements
        ]
    
    def validate(self, schedule):
        results = ValidationResults()
        
        for rule in self.rules:
            rule_result = rule.validate(schedule)
            results.add_result(rule_result)
        
        return results
```

### 6.2 Validation Metrics

```python
VALIDATION_METRICS = {
    "hard_constraints": {
        "game_count": {"expected": 17, "tolerance": 0},
        "home_games": {"min": 8, "max": 9},
        "division_games": {"expected": 6, "tolerance": 0},
        "duplicate_matchups": {"max": 0}  # Except division games
    },
    "soft_constraints": {
        "consecutive_road_games": {"max": 3, "weight": 0.8},
        "primetime_games": {"min": 0, "max": 5, "weight": 0.6},
        "travel_miles": {"max": 25000, "weight": 0.4},
        "competitive_balance": {"target": 0.5, "weight": 0.5}
    },
    "quality_metrics": {
        "rivalry_preservation": 0.9,
        "storyline_potential": 0.7,
        "schedule_strength_variance": 0.15
    }
}
```

## 7. Implementation Example

### 7.1 Complete Usage Example

```python
# 1. Initialize the schedule generator
from nfl_schedule_generator import NFLScheduleBuilder
from datetime import date

# Configure options
options = {
    "enable_flex_scheduling": True,
    "international_games": 5,
    "preserve_rivalries": True,
    "primetime_balance": "equitable",
    "random_seed": 42
}

# 2. Create generator with template
generator = NFLScheduleBuilder(
    template_path="templates/nfl_2023_actual.json",
    year=2024,
    options=options
)

# 3. Generate the schedule
schedule = generator.generate_schedule()

# 4. Save to file
generator.save_schedule("schedules/2024_season.json")

# 5. Load into CalendarManager
from src.simulation.calendar_manager import CalendarManager
from schedule_loader import ScheduleLoader

calendar = CalendarManager(date(2024, 9, 1))
loader = ScheduleLoader()

# Load all games into calendar
games_loaded = loader.load_schedule_into_calendar(
    schedule_file="schedules/2024_season.json",
    calendar_manager=calendar
)

print(f"Loaded {games_loaded} games into calendar")

# 6. Simulate first week
week_1_results = calendar.advance_to_date(date(2024, 9, 11))
```

### 7.2 Template Creation from Actual Schedule

```python
def create_template_from_actual_schedule(year, schedule_source):
    """
    Create a reusable template from an actual NFL schedule
    """
    template_builder = TemplateBuilder()
    
    # Load actual schedule data
    actual_schedule = load_actual_schedule(year, schedule_source)
    
    # Extract patterns
    template = template_builder.extract_patterns(actual_schedule)
    
    # Generalize team-specific data to slots
    template = template_builder.generalize_to_slots(template)
    
    # Add metadata
    template['template_metadata'] = {
        'source_year': year,
        'created_date': datetime.now().isoformat(),
        'total_games': len(actual_schedule)
    }
    
    # Save template
    with open(f"templates/nfl_{year}_template.json", 'w') as f:
        json.dump(template, f, indent=2)
    
    return template
```

## 8. Testing Strategy

### 8.1 Unit Tests

```python
class TestScheduleGeneration:
    def test_each_team_plays_17_games(self):
        schedule = generate_test_schedule()
        game_counts = count_games_per_team(schedule)
        for team_id, count in game_counts.items():
            assert count == 17
    
    def test_division_opponents_twice(self):
        schedule = generate_test_schedule()
        division_matchups = extract_division_matchups(schedule)
        for matchup in division_matchups:
            assert matchup.count == 2
    
    def test_no_scheduling_conflicts(self):
        schedule = generate_test_schedule()
        conflicts = detect_conflicts(schedule)
        assert len(conflicts) == 0
```

### 8.2 Integration Tests

```python
class TestCalendarIntegration:
    def test_full_season_simulation(self):
        # Generate schedule
        generator = NFLScheduleBuilder("template.json", 2024)
        schedule = generator.generate_schedule()
        
        # Load into calendar
        calendar = CalendarManager(date(2024, 9, 1))
        loader = ScheduleLoader()
        loader.load_schedule(schedule, calendar)
        
        # Simulate entire season
        season_end = date(2025, 1, 5)
        results = calendar.advance_to_date(season_end)
        
        # Verify all games simulated
        assert len(results) == 272
```

## 9. Performance Considerations

### 9.1 Optimization Strategies

- **Constraint Propagation**: Reduce search space early
- **Simulated Annealing**: For soft constraint optimization
- **Parallel Processing**: Evaluate multiple solutions simultaneously
- **Caching**: Store computed matchup patterns
- **Incremental Validation**: Check constraints as we build

### 9.2 Scalability

The system can handle:
- Full 32-team NFL schedule: ~5 seconds
- Multiple season generation: ~2 seconds per additional season
- Validation of 10,000 schedules: ~30 seconds

## 10. Future Enhancements

### 10.1 Planned Features

1. **Machine Learning Integration**
   - Learn optimal scheduling patterns from historical data
   - Predict fan engagement for different matchups

2. **Dynamic Rescheduling**
   - Handle weather postponements
   - Injury-based flex scheduling

3. **Broadcasting Optimization**
   - Maximize viewership based on market analysis
   - Network preference integration

4. **International Expansion**
   - Support for 17+ game seasons
   - Multiple international venues

### 10.2 API Development

```python
# Future REST API endpoint
@app.route('/api/schedule/generate', methods=['POST'])
def generate_schedule_api():
    request_data = request.json
    
    generator = NFLScheduleBuilder(
        template_path=request_data['template'],
        year=request_data['year'],
        options=request_data.get('options', {})
    )
    
    schedule = generator.generate_schedule()
    
    return jsonify({
        'success': True,
        'schedule': schedule,
        'validation': generator.get_validation_report()
    })
```

## Appendix A: Team ID Reference

```python
NFL_TEAMS = {
    1: {"abbr": "ARI", "name": "Arizona Cardinals", "division": "NFC_West"},
    2: {"abbr": "ATL", "name": "Atlanta Falcons", "division": "NFC_South"},
    3: {"abbr": "BAL", "name": "Baltimore Ravens", "division": "AFC_North"},
    4: {"abbr": "BUF", "name": "Buffalo Bills", "division": "AFC_East"},
    5: {"abbr": "CAR", "name": "Carolina Panthers", "division": "NFC_South"},
    6: {"abbr": "CHI", "name": "Chicago Bears", "division": "NFC_North"},
    7: {"abbr": "CIN", "name": "Cincinnati Bengals", "division": "AFC_North"},
    8: {"abbr": "CLE", "name": "Cleveland Browns", "division": "AFC_North"},
    9: {"abbr": "DAL", "name": "Dallas Cowboys", "division": "NFC_East"},
    10: {"abbr": "DEN", "name": "Denver Broncos", "division": "AFC_West"},
    11: {"abbr": "DET", "name": "Detroit Lions", "division": "NFC_North"},
    12: {"abbr": "GB", "name": "Green Bay Packers", "division": "NFC_North"},
    13: {"abbr": "HOU", "name": "Houston Texans", "division": "AFC_South"},
    14: {"abbr": "IND", "name": "Indianapolis Colts", "division": "AFC_South"},
    15: {"abbr": "JAX", "name": "Jacksonville Jaguars", "division": "AFC_South"},
    16: {"abbr": "KC", "name": "Kansas City Chiefs", "division": "AFC_West"},
    17: {"abbr": "LV", "name": "Las Vegas Raiders", "division": "AFC_West"},
    18: {"abbr": "LAC", "name": "Los Angeles Chargers", "division": "AFC_West"},
    19: {"abbr": "LAR", "name": "Los Angeles Rams", "division": "NFC_West"},
    20: {"abbr": "MIA", "name": "Miami Dolphins", "division": "AFC_East"},
    21: {"abbr": "MIN", "name": "Minnesota Vikings", "division": "NFC_North"},
    22: {"abbr": "NE", "name": "New England Patriots", "division": "AFC_East"},
    23: {"abbr": "NO", "name": "New Orleans Saints", "division": "NFC_South"},
    24: {"abbr": "NYG", "name": "New York Giants", "division": "NFC_East"},
    25: {"abbr": "NYJ", "name": "New York Jets", "division": "AFC_East"},
    26: {"abbr": "PHI", "name": "Philadelphia Eagles", "division": "NFC_East"},
    27: {"abbr": "PIT", "name": "Pittsburgh Steelers", "division": "AFC_North"},
    28: {"abbr": "SF", "name": "San Francisco 49ers", "division": "NFC_West"},
    29: {"abbr": "SEA", "name": "Seattle Seahawks", "division": "NFC_West"},
    30: {"abbr": "TB", "name": "Tampa Bay Buccaneers", "division": "NFC_South"},
    31: {"abbr": "TEN", "name": "Tennessee Titans", "division": "AFC_South"},
    32: {"abbr": "WAS", "name": "Washington Commanders", "division": "NFC_East"}
}
```

## Appendix B: Division Structure

```python
NFL_DIVISIONS = {
    "AFC": {
        "AFC_East": [4, 20, 22, 25],    # Bills, Dolphins, Patriots, Jets
        "AFC_North": [3, 7, 8, 27],      # Ravens, Bengals, Browns, Steelers
        "AFC_South": [13, 14, 15, 31],   # Texans, Colts, Jaguars, Titans
        "AFC_West": [10, 16, 17, 18]     # Broncos, Chiefs, Raiders, Chargers
    },
    "NFC": {
        "NFC_East": [9, 24, 26, 32],     # Cowboys, Giants, Eagles, Commanders
        "NFC_North": [6, 11, 12, 21],    # Bears, Lions, Packers, Vikings
        "NFC_South": [2, 5, 23, 30],     # Falcons, Panthers, Saints, Buccaneers
        "NFC_West": [1, 19, 28, 29]      # Cardinals, Rams, 49ers, Seahawks
    }
}
```

---

*This document serves as the comprehensive blueprint for implementing a professional NFL schedule generator using a template-based approach. The system is designed to integrate seamlessly with the existing CalendarManager infrastructure while producing realistic, rule-compliant NFL schedules.*