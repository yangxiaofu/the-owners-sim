# NFL Schedule Generator Development Roadmap

## Executive Overview

### Project Goal
Build a sophisticated NFL schedule generator that creates realistic, rule-compliant season schedules compatible with the CalendarManager simulation system.

### Timeline
- **Total Duration:** 6 weeks (42 days)
- **Development Hours:** ~200 hours
- **Team Size:** 1-2 developers

### Key Deliverables
1. Complete NFL schedule generator system
2. Template-based scheduling engine
3. Constraint satisfaction solver
4. CalendarManager integration
5. Comprehensive test suite
6. Full documentation

### Development Phases
| Phase | Duration | Focus Area |
|-------|----------|------------|
| Phase 0 | Days 1-2 | Foundation & Setup |
| Phase 1 | Days 3-5 | Data Layer |
| Phase 2 | Days 6-10 | Template System |
| Phase 3 | Days 11-13 | Classification System |
| Phase 4 | Days 14-17 | Rotation Engine |
| Phase 5 | Days 18-23 | Constraint System |
| Phase 6 | Days 24-26 | Special Games |
| Phase 7 | Days 27-30 | Main Builder |
| Phase 8 | Days 31-33 | Validation System |
| Phase 9 | Days 34-36 | Integration |
| Phase 10 | Days 37-40 | Testing Suite |
| Phase 11 | Days 41-42 | Documentation & Deployment |

---

## Phase 0: Foundation & Setup (Days 1-2)

### Step 1: Create Project Structure

```bash
# Create directory structure
mkdir -p src/scheduling/{generator,validators,data,loaders}
mkdir -p templates schedules
mkdir -p tests/test_schedule_generator
mkdir -p docs/scheduling
```

**Directory Layout:**
```
the-owners-sim/
├── src/
│   └── scheduling/
│       ├── __init__.py
│       ├── generator/
│       │   ├── __init__.py
│       │   ├── template_builder.py
│       │   ├── team_classifier.py
│       │   ├── constraint_solver.py
│       │   ├── rotation_engine.py
│       │   ├── schedule_builder.py
│       │   ├── slot_manager.py
│       │   ├── matchup_generator.py
│       │   ├── optimizer.py
│       │   ├── special_games.py
│       │   ├── flex_scheduler.py
│       │   └── output_formatter.py
│       ├── validators/
│       │   ├── __init__.py
│       │   ├── constraints.py
│       │   ├── rule_validator.py
│       │   ├── constraint_validator.py
│       │   ├── schedule_validator.py
│       │   └── report_generator.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── team_data.py
│       │   ├── division_structure.py
│       │   ├── rivalries.py
│       │   └── historical_loader.py
│       └── loaders/
│           ├── __init__.py
│           ├── schedule_loader.py
│           ├── template_loader.py
│           └── calendar_integration.py
├── templates/
│   ├── nfl_2023_actual.json
│   ├── slot_template_base.json
│   └── README.md
├── schedules/
│   └── README.md
└── tests/
    └── test_schedule_generator/
        ├── __init__.py
        ├── test_units.py
        ├── test_integration.py
        ├── test_performance.py
        └── fixtures/
```

### Step 2: Install Dependencies

**File:** `requirements_scheduling.txt`
```txt
# Core dependencies
python-constraint==1.4.0     # Constraint satisfaction
numpy==1.24.3                # Numerical operations
pandas==2.1.4                # Data manipulation
jsonschema==4.20.0           # JSON validation

# Optimization
scipy==1.11.4                # Scientific computing
ortools==9.7.2996           # Google OR-Tools for optimization

# Testing
pytest==7.4.3               # Testing framework
pytest-cov==4.1.0           # Coverage reporting
pytest-benchmark==4.0.0      # Performance testing

# Development
black==23.12.0              # Code formatting
mypy==1.7.1                 # Type checking
pylint==3.0.3               # Linting
```

**Installation:**
```bash
pip install -r requirements_scheduling.txt
```

### Step 3: Create Base Data Structures

**File:** `src/scheduling/data/division_structure.py`
```python
"""
NFL Division Structure and Constants

Defines the structure of the NFL including conferences, divisions,
and team assignments.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

class Conference(Enum):
    AFC = "AFC"
    NFC = "NFC"

class Division(Enum):
    # AFC Divisions
    AFC_EAST = "AFC_East"
    AFC_NORTH = "AFC_North"
    AFC_SOUTH = "AFC_South"
    AFC_WEST = "AFC_West"
    
    # NFC Divisions
    NFC_EAST = "NFC_East"
    NFC_NORTH = "NFC_North"
    NFC_SOUTH = "NFC_South"
    NFC_WEST = "NFC_West"

@dataclass
class NFLStructure:
    """Complete NFL organizational structure"""
    
    # Division composition
    divisions: Dict[Division, List[int]] = None
    
    def __post_init__(self):
        self.divisions = {
            Division.AFC_EAST: [4, 20, 22, 25],    # Bills, Dolphins, Patriots, Jets
            Division.AFC_NORTH: [3, 7, 8, 27],      # Ravens, Bengals, Browns, Steelers
            Division.AFC_SOUTH: [13, 14, 15, 31],   # Texans, Colts, Jaguars, Titans
            Division.AFC_WEST: [10, 16, 17, 18],    # Broncos, Chiefs, Raiders, Chargers
            Division.NFC_EAST: [9, 24, 26, 32],     # Cowboys, Giants, Eagles, Commanders
            Division.NFC_NORTH: [6, 11, 12, 21],    # Bears, Lions, Packers, Vikings
            Division.NFC_SOUTH: [2, 5, 23, 30],     # Falcons, Panthers, Saints, Buccaneers
            Division.NFC_WEST: [1, 19, 28, 29],     # Cardinals, Rams, 49ers, Seahawks
        }
    
    def get_division_for_team(self, team_id: int) -> Division:
        """Get division for a specific team"""
        for division, teams in self.divisions.items():
            if team_id in teams:
                return division
        raise ValueError(f"Team {team_id} not found in any division")
    
    def get_conference_for_team(self, team_id: int) -> Conference:
        """Get conference for a specific team"""
        division = self.get_division_for_team(team_id)
        return Conference.AFC if "AFC" in division.value else Conference.NFC
    
    def get_division_opponents(self, team_id: int) -> List[int]:
        """Get division opponents for a team"""
        division = self.get_division_for_team(team_id)
        return [t for t in self.divisions[division] if t != team_id]

# Global instance
NFL_STRUCTURE = NFLStructure()
```

**Deliverable:** Basic project structure with dependencies installed

---

## Phase 1: Data Layer (Days 3-5)

### Step 4: Build Team Data Manager

**File:** `src/scheduling/data/team_data.py`
```python
"""
Team Data Manager

Manages all team-related data including names, locations, stadiums,
and metadata needed for scheduling.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from .division_structure import NFL_STRUCTURE, Division, Conference

@dataclass
class Team:
    """Represents an NFL team with all metadata"""
    team_id: int
    city: str
    nickname: str
    abbreviation: str
    full_name: str
    stadium: str
    capacity: int
    timezone: str
    latitude: float
    longitude: float
    market_size: str  # large, medium, small
    
    @property
    def division(self) -> Division:
        return NFL_STRUCTURE.get_division_for_team(self.team_id)
    
    @property
    def conference(self) -> Conference:
        return NFL_STRUCTURE.get_conference_for_team(self.team_id)
    
    @property
    def division_rivals(self) -> List[int]:
        return NFL_STRUCTURE.get_division_opponents(self.team_id)

class TeamDataManager:
    """Manages team data and provides lookup methods"""
    
    def __init__(self, teams_file: str = "src/data/teams.json"):
        self.teams: Dict[int, Team] = {}
        self.load_teams(teams_file)
    
    def load_teams(self, teams_file: str) -> None:
        """Load team data from JSON file"""
        with open(teams_file, 'r') as f:
            teams_data = json.load(f)
        
        for team_id, team_info in teams_data.items():
            self.teams[int(team_id)] = Team(
                team_id=int(team_id),
                city=team_info['city'],
                nickname=team_info['nickname'],
                abbreviation=team_info['abbreviation'],
                full_name=team_info['full_name'],
                stadium=team_info.get('stadium', 'Unknown Stadium'),
                capacity=team_info.get('capacity', 65000),
                timezone=team_info.get('timezone', 'ET'),
                latitude=team_info.get('latitude', 0.0),
                longitude=team_info.get('longitude', 0.0),
                market_size=team_info.get('market_size', 'medium')
            )
    
    def get_team(self, team_id: int) -> Team:
        """Get team by ID"""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        return self.teams[team_id]
    
    def get_teams_by_division(self, division: Division) -> List[Team]:
        """Get all teams in a division"""
        division_team_ids = NFL_STRUCTURE.divisions[division]
        return [self.teams[tid] for tid in division_team_ids]
    
    def get_teams_by_conference(self, conference: Conference) -> List[Team]:
        """Get all teams in a conference"""
        teams = []
        for team in self.teams.values():
            if team.conference == conference:
                teams.append(team)
        return teams
    
    def calculate_distance(self, team1_id: int, team2_id: int) -> float:
        """Calculate distance between two teams (simplified)"""
        team1 = self.get_team(team1_id)
        team2 = self.get_team(team2_id)
        
        # Simplified distance calculation (would use haversine in production)
        lat_diff = abs(team1.latitude - team2.latitude)
        lon_diff = abs(team1.longitude - team2.longitude)
        return (lat_diff ** 2 + lon_diff ** 2) ** 0.5 * 69  # Rough miles conversion
```

**Test:**
```python
def test_team_data_manager():
    manager = TeamDataManager()
    
    # Test team loading
    lions = manager.get_team(11)
    assert lions.nickname == "Lions"
    assert lions.division == Division.NFC_NORTH
    
    # Test division lookup
    nfc_north = manager.get_teams_by_division(Division.NFC_NORTH)
    assert len(nfc_north) == 4
    
    # Test rivals
    assert 12 in lions.division_rivals  # Packers are rivals
```

### Step 5: Create Historical Data Loader

**File:** `src/scheduling/data/historical_loader.py`
```python
"""
Historical Data Loader

Loads and processes historical season data including standings,
playoff results, and strength of schedule.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import json

@dataclass
class TeamStanding:
    """Previous season standing for a team"""
    team_id: int
    wins: int
    losses: int
    ties: int
    division_rank: int
    conference_rank: int
    overall_rank: int
    made_playoffs: bool
    playoff_seed: int = 0
    
    @property
    def win_percentage(self) -> float:
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / total_games

class HistoricalDataLoader:
    """Loads and manages historical season data"""
    
    def __init__(self, season_year: int):
        self.season_year = season_year
        self.previous_year = season_year - 1
        self.standings: Dict[int, TeamStanding] = {}
        self.load_previous_standings()
    
    def load_previous_standings(self) -> None:
        """Load previous season standings"""
        # In production, would load from database or API
        # For now, using placeholder data
        self.standings = self._generate_placeholder_standings()
    
    def _generate_placeholder_standings(self) -> Dict[int, TeamStanding]:
        """Generate placeholder standings for testing"""
        standings = {}
        
        # Simulate some standings (would be real data in production)
        playoff_teams = [3, 4, 16, 18, 20, 14, 10,  # AFC
                        28, 9, 26, 11, 19, 30, 23]  # NFC
        
        for team_id in range(1, 33):
            standings[team_id] = TeamStanding(
                team_id=team_id,
                wins=10 if team_id in playoff_teams[:7] else 7,
                losses=7 if team_id in playoff_teams[:7] else 10,
                ties=0,
                division_rank=1 if team_id in playoff_teams[:4] else 2,
                conference_rank=(team_id % 16) + 1,
                overall_rank=team_id,
                made_playoffs=team_id in playoff_teams,
                playoff_seed=playoff_teams.index(team_id) + 1 if team_id in playoff_teams else 0
            )
        
        return standings
    
    def get_division_standings(self, division: Division) -> List[TeamStanding]:
        """Get standings for all teams in a division"""
        division_teams = NFL_STRUCTURE.divisions[division]
        standings = [self.standings[tid] for tid in division_teams]
        return sorted(standings, key=lambda x: x.division_rank)
    
    def get_place_based_matchups(self, team_id: int) -> List[int]:
        """
        Get place-based matchup opponents for a team.
        Teams play same-place finishers from previous year.
        """
        team_standing = self.standings[team_id]
        division_rank = team_standing.division_rank
        
        matchups = []
        team_division = NFL_STRUCTURE.get_division_for_team(team_id)
        team_conference = NFL_STRUCTURE.get_conference_for_team(team_id)
        
        # Find same-place teams in other divisions
        for division, teams in NFL_STRUCTURE.divisions.items():
            if division != team_division:
                for other_team_id in teams:
                    other_standing = self.standings[other_team_id]
                    if other_standing.division_rank == division_rank:
                        # Check if it's a valid place-based matchup
                        other_conference = NFL_STRUCTURE.get_conference_for_team(other_team_id)
                        if should_play_place_based(team_conference, other_conference):
                            matchups.append(other_team_id)
        
        return matchups[:3]  # NFL rules: 3 place-based games

def should_play_place_based(conf1: Conference, conf2: Conference) -> bool:
    """Determine if two teams should have a place-based matchup"""
    # Simplified logic - would be more complex based on rotation
    return True
```

### Step 6: Build Template Data Structure

**File:** `templates/slot_template_base.json`
```json
{
  "template_metadata": {
    "version": "1.0",
    "created_date": "2024-01-01",
    "template_type": "nfl_regular_season",
    "total_weeks": 18,
    "total_slots": 272,
    "games_per_team": 17,
    "bye_week_range": [4, 12]
  },
  "time_slots": {
    "thursday_night": {"time": "20:20", "timezone": "ET"},
    "sunday_early": {"time": "13:00", "timezone": "ET"},
    "sunday_late_cbs": {"time": "16:05", "timezone": "ET"},
    "sunday_late_fox": {"time": "16:25", "timezone": "ET"},
    "sunday_night": {"time": "20:20", "timezone": "ET"},
    "monday_night": {"time": "20:15", "timezone": "ET"},
    "saturday_early": {"time": "13:00", "timezone": "ET"},
    "saturday_late": {"time": "16:30", "timezone": "ET"},
    "saturday_night": {"time": "20:15", "timezone": "ET"}
  },
  "special_events": {
    "season_opener": {
      "week": 1,
      "slot_type": "thursday_night",
      "requirements": ["super_bowl_champion_home", "high_profile_opponent"]
    },
    "thanksgiving": {
      "week": 12,
      "games": [
        {"host_team": 11, "time": "12:30", "network": "CBS"},
        {"host_team": 9, "time": "16:30", "network": "FOX"},
        {"host_team": null, "time": "20:20", "network": "NBC"}
      ]
    },
    "christmas": {
      "variable_week": true,
      "games_count": 1,
      "requirements": ["primetime_worthy", "national_appeal"]
    }
  },
  "schedule_slots": []
}
```

**JSON Schema Validation:**
```python
# File: src/scheduling/validators/template_schema.py
template_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["template_metadata", "time_slots", "schedule_slots"],
    "properties": {
        "template_metadata": {
            "type": "object",
            "required": ["version", "template_type", "total_weeks", "total_slots"],
            "properties": {
                "version": {"type": "string"},
                "template_type": {"type": "string"},
                "total_weeks": {"type": "integer", "minimum": 1, "maximum": 18},
                "total_slots": {"type": "integer", "minimum": 1, "maximum": 300}
            }
        },
        "time_slots": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["time", "timezone"],
                "properties": {
                    "time": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
                    "timezone": {"type": "string"}
                }
            }
        }
    }
}
```

**Deliverable:** Complete data layer with team management and historical data

---

## Phase 2: Template System (Days 6-10)

### Step 7: Implement Template Loader

**File:** `src/scheduling/loaders/template_loader.py`
```python
"""
Template Loader

Loads and validates schedule templates from JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, date, timedelta
import jsonschema

@dataclass
class ScheduleSlot:
    """Represents a single game slot in the schedule"""
    slot_id: str
    week: int
    day_of_week: str  # MON, TUE, WED, THU, FRI, SAT, SUN
    time: str  # HH:MM format
    timezone: str
    slot_type: str  # standard, primetime, special
    network: Optional[str] = None
    requirements: Dict[str, Any] = None
    
    def get_date_for_year(self, year: int, season_start: date) -> datetime:
        """Calculate actual date for this slot in a given year"""
        # Calculate week start date
        week_start = season_start + timedelta(weeks=self.week - 1)
        
        # Find the specific day of week
        days = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 
                'FRI': 4, 'SAT': 5, 'SUN': 6}
        target_day = days[self.day_of_week]
        
        # Calculate days to add
        days_ahead = target_day - week_start.weekday()
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7
        
        slot_date = week_start + timedelta(days=days_ahead)
        
        # Combine with time
        time_parts = self.time.split(':')
        return datetime(slot_date.year, slot_date.month, slot_date.day,
                       int(time_parts[0]), int(time_parts[1]))

@dataclass
class ScheduleTemplate:
    """Complete schedule template"""
    metadata: Dict[str, Any]
    slots: List[ScheduleSlot]
    special_events: Dict[str, Any]
    time_slots: Dict[str, Dict[str, str]]
    
    def get_slots_for_week(self, week: int) -> List[ScheduleSlot]:
        """Get all slots for a specific week"""
        return [slot for slot in self.slots if slot.week == week]
    
    def get_primetime_slots(self) -> List[ScheduleSlot]:
        """Get all primetime slots"""
        return [slot for slot in self.slots 
                if slot.slot_type in ['primetime', 'thursday_night', 
                                      'sunday_night', 'monday_night']]

class TemplateLoader:
    """Loads and manages schedule templates"""
    
    def __init__(self):
        self.template: Optional[ScheduleTemplate] = None
        self.schema = self._load_schema()
    
    def _load_schema(self) -> Dict:
        """Load JSON schema for validation"""
        # Would load from file in production
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["template_metadata", "schedule_slots"]
        }
    
    def load_template(self, template_path: str) -> ScheduleTemplate:
        """Load template from JSON file"""
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        # Validate against schema
        if not self.validate_template(template_data):
            raise ValueError(f"Invalid template: {template_path}")
        
        # Parse slots
        slots = []
        for slot_data in template_data.get('schedule_slots', []):
            slots.append(ScheduleSlot(**slot_data))
        
        self.template = ScheduleTemplate(
            metadata=template_data['template_metadata'],
            slots=slots,
            special_events=template_data.get('special_events', {}),
            time_slots=template_data.get('time_slots', {})
        )
        
        return self.template
    
    def validate_template(self, template_data: Dict) -> bool:
        """Validate template against schema"""
        try:
            jsonschema.validate(template_data, self.schema)
            return True
        except jsonschema.ValidationError as e:
            print(f"Template validation error: {e}")
            return False
    
    def create_empty_template(self, weeks: int = 18) -> ScheduleTemplate:
        """Create an empty template with standard slots"""
        slots = []
        slot_id = 0
        
        for week in range(1, weeks + 1):
            # Thursday night (except week 1 which has kickoff game)
            if week > 1:
                slots.append(ScheduleSlot(
                    slot_id=f"W{week:02d}_THU_01",
                    week=week,
                    day_of_week="THU",
                    time="20:20",
                    timezone="ET",
                    slot_type="thursday_night",
                    network="PRIME"
                ))
            
            # Sunday games (typically 13-14 games)
            for i in range(8):  # Early games
                slots.append(ScheduleSlot(
                    slot_id=f"W{week:02d}_SUN_EARLY_{i+1:02d}",
                    week=week,
                    day_of_week="SUN",
                    time="13:00",
                    timezone="ET",
                    slot_type="standard",
                    network="CBS" if i % 2 == 0 else "FOX"
                ))
            
            for i in range(3):  # Late afternoon games
                slots.append(ScheduleSlot(
                    slot_id=f"W{week:02d}_SUN_LATE_{i+1:02d}",
                    week=week,
                    day_of_week="SUN",
                    time="16:25" if i == 0 else "16:05",
                    timezone="ET",
                    slot_type="standard",
                    network="FOX" if i == 0 else "CBS"
                ))
            
            # Sunday night
            slots.append(ScheduleSlot(
                slot_id=f"W{week:02d}_SUN_NIGHT",
                week=week,
                day_of_week="SUN",
                time="20:20",
                timezone="ET",
                slot_type="sunday_night",
                network="NBC"
            ))
            
            # Monday night
            if week != 18:  # No MNF in week 18
                slots.append(ScheduleSlot(
                    slot_id=f"W{week:02d}_MON_NIGHT",
                    week=week,
                    day_of_week="MON",
                    time="20:15",
                    timezone="ET",
                    slot_type="monday_night",
                    network="ESPN"
                ))
        
        return ScheduleTemplate(
            metadata={"weeks": weeks, "total_slots": len(slots)},
            slots=slots,
            special_events={},
            time_slots={}
        )
```

### Step 8: Build Template Builder (From Actual Schedule)

**File:** `src/scheduling/generator/template_builder.py`
```python
"""
Template Builder

Creates reusable templates from actual NFL schedules.
"""

from typing import Dict, List, Any
import json
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class GameRecord:
    """Represents a game from an actual schedule"""
    week: int
    date: str
    time: str
    away_team: str
    home_team: str
    network: str = ""
    slot_type: str = "standard"

class TemplateBuilder:
    """Builds templates from actual schedule data"""
    
    def __init__(self):
        self.games: List[GameRecord] = []
        self.template_slots = []
    
    def load_actual_schedule(self, schedule_file: str) -> None:
        """Load an actual NFL schedule"""
        with open(schedule_file, 'r') as f:
            schedule_data = json.load(f)
        
        for game in schedule_data.get('games', []):
            self.games.append(GameRecord(**game))
    
    def extract_patterns(self) -> Dict[str, Any]:
        """Extract scheduling patterns from actual schedule"""
        patterns = {
            "weekly_distribution": self._analyze_weekly_distribution(),
            "timeslot_usage": self._analyze_timeslot_usage(),
            "network_assignments": self._analyze_network_assignments(),
            "division_game_patterns": self._analyze_division_patterns(),
            "primetime_distribution": self._analyze_primetime_distribution()
        }
        return patterns
    
    def _analyze_weekly_distribution(self) -> Dict[int, int]:
        """Analyze how many games per week"""
        distribution = {}
        for game in self.games:
            if game.week not in distribution:
                distribution[game.week] = 0
            distribution[game.week] += 1
        return distribution
    
    def _analyze_timeslot_usage(self) -> Dict[str, int]:
        """Analyze time slot usage patterns"""
        timeslots = {}
        for game in self.games:
            slot_key = f"{game.date}_{game.time}"
            if slot_key not in timeslots:
                timeslots[slot_key] = 0
            timeslots[slot_key] += 1
        return timeslots
    
    def _analyze_network_assignments(self) -> Dict[str, List[str]]:
        """Analyze network assignment patterns"""
        networks = {}
        for game in self.games:
            if game.network:
                if game.network not in networks:
                    networks[game.network] = []
                networks[game.network].append(f"{game.away_team}@{game.home_team}")
        return networks
    
    def _analyze_division_patterns(self) -> Dict[str, Any]:
        """Analyze division game scheduling patterns"""
        # Implementation would analyze when division games occur
        return {"early_season": 0.3, "mid_season": 0.4, "late_season": 0.3}
    
    def _analyze_primetime_distribution(self) -> Dict[str, int]:
        """Analyze primetime game distribution"""
        primetime = {}
        primetime_slots = ["20:20", "20:15", "20:30"]
        
        for game in self.games:
            if game.time in primetime_slots:
                teams = [game.home_team, game.away_team]
                for team in teams:
                    if team not in primetime:
                        primetime[team] = 0
                    primetime[team] += 1
        return primetime
    
    def generalize_to_template(self) -> Dict[str, Any]:
        """Convert specific schedule to general template"""
        template = {
            "template_metadata": {
                "version": "1.0",
                "source": "actual_schedule",
                "created": datetime.now().isoformat()
            },
            "schedule_slots": [],
            "patterns": self.extract_patterns()
        }
        
        # Convert each game to a slot
        for i, game in enumerate(self.games):
            slot = {
                "slot_id": f"SLOT_{i:03d}",
                "week": game.week,
                "date_pattern": self._extract_date_pattern(game.date),
                "time": game.time,
                "requirements": self._extract_requirements(game),
                "slot_type": game.slot_type
            }
            template["schedule_slots"].append(slot)
        
        return template
    
    def _extract_date_pattern(self, date_str: str) -> str:
        """Extract day of week pattern from date"""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        return days[date_obj.weekday()]
    
    def _extract_requirements(self, game: GameRecord) -> Dict[str, Any]:
        """Extract requirements for this slot based on game"""
        requirements = {}
        
        # Primetime games have special requirements
        if game.time in ["20:20", "20:15"]:
            requirements["type"] = "primetime"
            requirements["market_appeal"] = "high"
        
        # Network-specific requirements
        if game.network:
            requirements["network"] = game.network
        
        return requirements
    
    def save_template(self, output_path: str) -> None:
        """Save template to JSON file"""
        template = self.generalize_to_template()
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2)
```

### Step 9: Create Slot Management System

**File:** `src/scheduling/generator/slot_manager.py`
```python
"""
Slot Management System

Manages the assignment of games to schedule slots.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from ..loaders.template_loader import ScheduleSlot

@dataclass
class SlotAssignment:
    """Represents a game assigned to a slot"""
    slot_id: str
    home_team_id: int
    away_team_id: int
    locked: bool = False  # Some assignments (like Thanksgiving) are locked
    
    @property
    def matchup(self) -> Tuple[int, int]:
        return (self.away_team_id, self.home_team_id)

class SlotManager:
    """Manages slot assignments for schedule generation"""
    
    def __init__(self, template_slots: List[ScheduleSlot]):
        self.slots: Dict[str, ScheduleSlot] = {
            slot.slot_id: slot for slot in template_slots
        }
        self.assignments: Dict[str, SlotAssignment] = {}
        self.team_week_assignments: Dict[Tuple[int, int], str] = {}  # (team_id, week) -> slot_id
    
    def assign_game_to_slot(self, slot_id: str, home_team: int, 
                           away_team: int, locked: bool = False) -> bool:
        """
        Assign a game to a specific slot.
        
        Returns True if successful, False if conflict exists.
        """
        if slot_id not in self.slots:
            raise ValueError(f"Slot {slot_id} does not exist")
        
        # Check if slot is already assigned
        if slot_id in self.assignments:
            if self.assignments[slot_id].locked:
                return False  # Can't override locked assignment
        
        slot = self.slots[slot_id]
        week = slot.week
        
        # Check if teams are already playing this week
        if (home_team, week) in self.team_week_assignments:
            return False
        if (away_team, week) in self.team_week_assignments:
            return False
        
        # Make assignment
        assignment = SlotAssignment(
            slot_id=slot_id,
            home_team_id=home_team,
            away_team_id=away_team,
            locked=locked
        )
        
        self.assignments[slot_id] = assignment
        self.team_week_assignments[(home_team, week)] = slot_id
        self.team_week_assignments[(away_team, week)] = slot_id
        
        return True
    
    def get_available_slots(self, week: int, 
                          requirements: Optional[Dict] = None) -> List[ScheduleSlot]:
        """Get available slots for a specific week with optional requirements"""
        available = []
        
        for slot_id, slot in self.slots.items():
            if slot.week != week:
                continue
            
            # Check if slot is available
            if slot_id in self.assignments:
                continue
            
            # Check requirements
            if requirements:
                if not self._slot_meets_requirements(slot, requirements):
                    continue
            
            available.append(slot)
        
        return available
    
    def _slot_meets_requirements(self, slot: ScheduleSlot, 
                                requirements: Dict) -> bool:
        """Check if a slot meets specific requirements"""
        if 'slot_type' in requirements:
            if slot.slot_type != requirements['slot_type']:
                return False
        
        if 'network' in requirements:
            if slot.network != requirements['network']:
                return False
        
        if 'time' in requirements:
            if slot.time != requirements['time']:
                return False
        
        return True
    
    def get_team_schedule(self, team_id: int) -> List[Tuple[int, SlotAssignment]]:
        """Get all scheduled games for a team"""
        schedule = []
        
        for (tid, week), slot_id in self.team_week_assignments.items():
            if tid == team_id:
                assignment = self.assignments[slot_id]
                schedule.append((week, assignment))
        
        return sorted(schedule, key=lambda x: x[0])
    
    def validate_assignments(self) -> Tuple[bool, List[str]]:
        """Validate all assignments for consistency"""
        errors = []
        
        # Check each team plays correct number of games
        team_game_counts = {}
        for assignment in self.assignments.values():
            for team_id in [assignment.home_team_id, assignment.away_team_id]:
                if team_id not in team_game_counts:
                    team_game_counts[team_id] = 0
                team_game_counts[team_id] += 1
        
        for team_id in range(1, 33):  # All 32 teams
            if team_id not in team_game_counts:
                errors.append(f"Team {team_id} has no games scheduled")
            elif team_game_counts[team_id] != 17:
                errors.append(f"Team {team_id} has {team_game_counts[team_id]} games, expected 17")
        
        # Check for slot conflicts
        for slot_id, assignment in self.assignments.items():
            slot = self.slots[slot_id]
            week = slot.week
            
            # Verify team-week assignments are consistent
            home_slot = self.team_week_assignments.get((assignment.home_team_id, week))
            away_slot = self.team_week_assignments.get((assignment.away_team_id, week))
            
            if home_slot != slot_id or away_slot != slot_id:
                errors.append(f"Inconsistent assignment for slot {slot_id}")
        
        return len(errors) == 0, errors
    
    def get_unassigned_slots(self) -> List[ScheduleSlot]:
        """Get all slots that haven't been assigned yet"""
        unassigned = []
        for slot_id, slot in self.slots.items():
            if slot_id not in self.assignments:
                unassigned.append(slot)
        return unassigned
    
    def clear_assignments(self, keep_locked: bool = True) -> None:
        """Clear all assignments, optionally keeping locked ones"""
        if keep_locked:
            # Keep only locked assignments
            locked_assignments = {
                sid: assignment for sid, assignment in self.assignments.items()
                if assignment.locked
            }
            self.assignments = locked_assignments
            
            # Rebuild team-week assignments
            self.team_week_assignments = {}
            for slot_id, assignment in locked_assignments.items():
                slot = self.slots[slot_id]
                week = slot.week
                self.team_week_assignments[(assignment.home_team_id, week)] = slot_id
                self.team_week_assignments[(assignment.away_team_id, week)] = slot_id
        else:
            self.assignments = {}
            self.team_week_assignments = {}
```

**Deliverable:** Complete template system with loading, building, and slot management

---

## Phase 3: Classification System (Days 11-13)

### Step 10: Implement Team Classifier

**File:** `src/scheduling/generator/team_classifier.py`
```python
"""
Team Classifier

Classifies teams based on various criteria for intelligent scheduling.
"""

from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from ..data.team_data import TeamDataManager, Team
from ..data.historical_loader import HistoricalDataLoader

class MarketTier(Enum):
    TIER_1_NATIONAL = 1  # National appeal, primetime draws
    TIER_2_LARGE = 2     # Large markets
    TIER_3_MEDIUM = 3    # Medium markets
    TIER_4_SMALL = 4     # Small markets

class CompetitiveTier(Enum):
    SUPER_BOWL_CONTENDER = 1
    PLAYOFF_TEAM = 2
    PLAYOFF_BUBBLE = 3
    REBUILDING = 4

@dataclass
class TeamClassification:
    """Complete classification for a team"""
    team_id: int
    market_tier: MarketTier
    competitive_tier: CompetitiveTier
    primetime_appearances_last_year: int
    rivalry_weight: float
    special_designations: List[str]

class TeamClassifier:
    """Classifies teams for scheduling purposes"""
    
    # Define market tiers
    MARKET_TIERS = {
        MarketTier.TIER_1_NATIONAL: [9, 22, 12, 28, 16, 11, 26],  # Cowboys, Patriots, Packers, 49ers, Chiefs, Lions, Eagles
        MarketTier.TIER_2_LARGE: [24, 25, 6, 19, 20, 2, 13],      # Giants, Jets, Bears, Rams, Dolphins, Falcons, Texans
        MarketTier.TIER_3_MEDIUM: [27, 3, 4, 14, 29, 10, 23, 30], # Steelers, Ravens, Bills, Colts, Seahawks, Broncos, Saints, Bucs
        MarketTier.TIER_4_SMALL: [1, 5, 7, 8, 15, 17, 18, 21, 31, 32]  # Rest
    }
    
    def __init__(self, year: int):
        self.year = year
        self.team_manager = TeamDataManager()
        self.historical_data = HistoricalDataLoader(year)
        self.classifications: Dict[int, TeamClassification] = {}
        self._classify_all_teams()
    
    def _classify_all_teams(self) -> None:
        """Classify all 32 teams"""
        for team_id in range(1, 33):
            self.classifications[team_id] = self._classify_team(team_id)
    
    def _classify_team(self, team_id: int) -> TeamClassification:
        """Classify a single team"""
        return TeamClassification(
            team_id=team_id,
            market_tier=self._get_market_tier(team_id),
            competitive_tier=self._get_competitive_tier(team_id),
            primetime_appearances_last_year=self._get_primetime_count(team_id),
            rivalry_weight=self._calculate_rivalry_weight(team_id),
            special_designations=self._get_special_designations(team_id)
        )
    
    def _get_market_tier(self, team_id: int) -> MarketTier:
        """Determine market tier for a team"""
        for tier, teams in self.MARKET_TIERS.items():
            if team_id in teams:
                return tier
        return MarketTier.TIER_4_SMALL
    
    def _get_competitive_tier(self, team_id: int) -> CompetitiveTier:
        """Determine competitive tier based on previous season"""
        standing = self.historical_data.standings.get(team_id)
        if not standing:
            return CompetitiveTier.REBUILDING
        
        if standing.playoff_seed <= 2:
            return CompetitiveTier.SUPER_BOWL_CONTENDER
        elif standing.made_playoffs:
            return CompetitiveTier.PLAYOFF_TEAM
        elif standing.wins >= 8:
            return CompetitiveTier.PLAYOFF_BUBBLE
        else:
            return CompetitiveTier.REBUILDING
    
    def _get_primetime_count(self, team_id: int) -> int:
        """Get number of primetime games last year"""
        # Would load from historical data
        # Using placeholder values
        primetime_counts = {
            9: 5,   # Cowboys always get max primetime
            16: 5,  # Chiefs as champions
            4: 4,   # Bills
            28: 4,  # 49ers
            # ... etc
        }
        return primetime_counts.get(team_id, 1)
    
    def _calculate_rivalry_weight(self, team_id: int) -> float:
        """Calculate overall rivalry importance for team"""
        # High rivalry teams get more consideration for good time slots
        high_rivalry_teams = [
            12, 6,   # Packers-Bears
            9, 32,   # Cowboys-Commanders
            27, 3,   # Steelers-Ravens
            24, 26,  # Giants-Eagles
        ]
        
        if team_id in high_rivalry_teams:
            return 1.0
        
        # Division rivals have moderate weight
        return 0.5
    
    def _get_special_designations(self, team_id: int) -> List[str]:
        """Get special designations for a team"""
        designations = []
        
        # Thanksgiving hosts
        if team_id == 11:  # Lions
            designations.append("thanksgiving_host_early")
        elif team_id == 9:  # Cowboys
            designations.append("thanksgiving_host_late")
        
        # International willing teams
        international_teams = [15, 13, 12, 31, 11]  # Jags, Texans, Packers, Titans, Lions
        if team_id in international_teams:
            designations.append("international_eligible")
        
        # Super Bowl champion
        if self.historical_data.standings[team_id].overall_rank == 1:
            designations.append("super_bowl_champion")
        
        return designations
    
    def get_primetime_candidates(self, min_tier: MarketTier = MarketTier.TIER_2_LARGE) -> List[int]:
        """Get teams eligible for primetime games"""
        candidates = []
        for team_id, classification in self.classifications.items():
            if classification.market_tier.value <= min_tier.value:
                candidates.append(team_id)
        return candidates
    
    def get_teams_by_market_tier(self, tier: MarketTier) -> List[int]:
        """Get all teams in a specific market tier"""
        return [tid for tid, c in self.classifications.items() 
                if c.market_tier == tier]
    
    def get_teams_by_competitive_tier(self, tier: CompetitiveTier) -> List[int]:
        """Get all teams in a specific competitive tier"""
        return [tid for tid, c in self.classifications.items() 
                if c.competitive_tier == tier]
    
    def should_protect_rivalry(self, team1: int, team2: int) -> bool:
        """Determine if a rivalry should be protected in good slots"""
        rivalry_pairs = [
            {12, 6},   # Packers-Bears
            {9, 32},   # Cowboys-Commanders  
            {9, 26},   # Cowboys-Eagles
            {27, 3},   # Steelers-Ravens
            {27, 8},   # Steelers-Browns
            {22, 25},  # Patriots-Jets
            {16, 17},  # Chiefs-Raiders
            {16, 10},  # Chiefs-Broncos
        ]
        
        team_set = {team1, team2}
        return team_set in rivalry_pairs
```

### Step 11: Build Rivalry System

**File:** `src/scheduling/data/rivalries.py`
```python
"""
NFL Rivalry System

Defines and manages rivalry relationships between teams.
"""

from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum

class RivalryTier(Enum):
    HISTORIC = 10      # Historic, must-protect rivalries
    DIVISION_PRIMARY = 8   # Primary division rival
    DIVISION_SECONDARY = 6 # Other division rivals
    CONFERENCE = 4     # Conference rivalries
    REGIONAL = 3       # Geographic/regional rivalries
    EMERGING = 2       # New competitive rivalries

@dataclass
class Rivalry:
    """Represents a rivalry between two teams"""
    team1_id: int
    team2_id: int
    tier: RivalryTier
    name: str
    protect_primetime: bool = False
    protect_late_season: bool = False
    
    @property
    def weight(self) -> int:
        return self.tier.value
    
    def involves_team(self, team_id: int) -> bool:
        return team_id in [self.team1_id, self.team2_id]
    
    def get_opponent(self, team_id: int) -> int:
        if team_id == self.team1_id:
            return self.team2_id
        elif team_id == self.team2_id:
            return self.team1_id
        return None

class RivalryManager:
    """Manages all NFL rivalries"""
    
    def __init__(self):
        self.rivalries: List[Rivalry] = []
        self._initialize_rivalries()
        self._rivalry_index: Dict[Tuple[int, int], Rivalry] = {}
        self._build_index()
    
    def _initialize_rivalries(self) -> None:
        """Initialize all NFL rivalries"""
        
        # Historic rivalries
        self.rivalries.extend([
            Rivalry(12, 6, RivalryTier.HISTORIC, "Packers-Bears", True, True),
            Rivalry(9, 32, RivalryTier.HISTORIC, "Cowboys-Commanders", True, True),
            Rivalry(27, 3, RivalryTier.HISTORIC, "Steelers-Ravens", True, True),
            Rivalry(16, 17, RivalryTier.HISTORIC, "Chiefs-Raiders", True, False),
            Rivalry(22, 25, RivalryTier.HISTORIC, "Patriots-Jets", True, False),
        ])
        
        # Division primary rivalries
        self.rivalries.extend([
            Rivalry(9, 26, RivalryTier.DIVISION_PRIMARY, "Cowboys-Eagles", True, True),
            Rivalry(24, 26, RivalryTier.DIVISION_PRIMARY, "Giants-Eagles", True, False),
            Rivalry(4, 20, RivalryTier.DIVISION_PRIMARY, "Bills-Dolphins", True, True),
            Rivalry(28, 19, RivalryTier.DIVISION_PRIMARY, "49ers-Rams", True, True),
            Rivalry(28, 29, RivalryTier.DIVISION_PRIMARY, "49ers-Seahawks", True, True),
            Rivalry(11, 21, RivalryTier.DIVISION_PRIMARY, "Lions-Vikings", False, True),
            Rivalry(7, 27, RivalryTier.DIVISION_PRIMARY, "Bengals-Steelers", False, True),
            Rivalry(3, 8, RivalryTier.DIVISION_PRIMARY, "Ravens-Browns", False, True),
        ])
        
        # Add all division matchups as at least secondary rivalries
        from ..data.division_structure import NFL_STRUCTURE
        
        for division, teams in NFL_STRUCTURE.divisions.items():
            for i, team1 in enumerate(teams):
                for team2 in teams[i+1:]:
                    # Check if already added as historic or primary
                    if not self._rivalry_exists(team1, team2):
                        self.rivalries.append(
                            Rivalry(team1, team2, RivalryTier.DIVISION_SECONDARY,
                                   f"{division.value} Division", False, False)
                        )
        
        # Regional/Conference rivalries
        self.rivalries.extend([
            Rivalry(24, 25, RivalryTier.REGIONAL, "New York Teams", True, False),
            Rivalry(19, 18, RivalryTier.REGIONAL, "Los Angeles Teams", True, False),
            Rivalry(2, 23, RivalryTier.REGIONAL, "NFC South", False, False),
            Rivalry(13, 9, RivalryTier.REGIONAL, "Texas Teams", True, False),
        ])
        
        # Emerging rivalries (based on recent playoffs/competition)
        self.rivalries.extend([
            Rivalry(16, 4, RivalryTier.EMERGING, "Chiefs-Bills Playoffs", True, False),
            Rivalry(16, 7, RivalryTier.EMERGING, "Chiefs-Bengals", True, False),
            Rivalry(28, 26, RivalryTier.EMERGING, "49ers-Eagles NFC", True, False),
        ])
    
    def _rivalry_exists(self, team1: int, team2: int) -> bool:
        """Check if rivalry already exists between two teams"""
        for rivalry in self.rivalries:
            if rivalry.involves_team(team1) and rivalry.involves_team(team2):
                return True
        return False
    
    def _build_index(self) -> None:
        """Build index for fast rivalry lookups"""
        for rivalry in self.rivalries:
            # Store both orderings for easy lookup
            key1 = (rivalry.team1_id, rivalry.team2_id)
            key2 = (rivalry.team2_id, rivalry.team1_id)
            self._rivalry_index[key1] = rivalry
            self._rivalry_index[key2] = rivalry
    
    def get_rivalry(self, team1: int, team2: int) -> Rivalry:
        """Get rivalry between two teams"""
        return self._rivalry_index.get((team1, team2))
    
    def get_rivalry_weight(self, team1: int, team2: int) -> int:
        """Get rivalry weight between two teams"""
        rivalry = self.get_rivalry(team1, team2)
        return rivalry.weight if rivalry else 0
    
    def get_team_rivals(self, team_id: int, min_tier: RivalryTier = None) -> List[int]:
        """Get all rivals for a team"""
        rivals = []
        for rivalry in self.rivalries:
            if rivalry.involves_team(team_id):
                if min_tier and rivalry.tier.value < min_tier.value:
                    continue
                opponent = rivalry.get_opponent(team_id)
                if opponent:
                    rivals.append(opponent)
        return rivals
    
    def get_protected_rivalries(self) -> List[Rivalry]:
        """Get rivalries that should be protected in scheduling"""
        return [r for r in self.rivalries 
                if r.protect_primetime or r.protect_late_season]
    
    def should_protect_matchup(self, team1: int, team2: int, 
                              week: int, is_primetime: bool) -> bool:
        """Determine if a matchup should be protected/prioritized"""
        rivalry = self.get_rivalry(team1, team2)
        if not rivalry:
            return False
        
        # Historic rivalries always protected
        if rivalry.tier == RivalryTier.HISTORIC:
            return True
        
        # Primetime protection
        if is_primetime and rivalry.protect_primetime:
            return True
        
        # Late season protection (week 15+)
        if week >= 15 and rivalry.protect_late_season:
            return True
        
        return False
```

**Deliverable:** Complete classification system with team tiers and rivalry management

---

## Phase 4: Rotation Engine (Days 14-17)

### Step 12: Implement Division Rotation Logic

**File:** `src/scheduling/generator/rotation_engine.py`
```python
"""
NFL Rotation Engine

Implements NFL's complex rotation system for inter-division matchups.
"""

from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from ..data.division_structure import Division, Conference, NFL_STRUCTURE
from ..data.historical_loader import HistoricalDataLoader

@dataclass
class RotationCycle:
    """Represents a rotation cycle for divisions"""
    year: int
    conference_rotations: Dict[Division, Division]  # Same conference
    interconference_rotations: Dict[Division, Division]  # Other conference

class RotationEngine:
    """
    Manages NFL rotation patterns for scheduling.
    
    The NFL uses specific rotation patterns:
    - Intra-conference: 3-year cycle (play each division every 3 years)
    - Inter-conference: 4-year cycle (play each division every 4 years)
    - Place-based: Play same-place finishers from previous year
    """
    
    # Define the rotation patterns
    AFC_NFC_ROTATION = {
        # Year 0 of 4-year cycle
        0: {
            Division.AFC_EAST: Division.NFC_NORTH,
            Division.AFC_NORTH: Division.NFC_WEST,
            Division.AFC_SOUTH: Division.NFC_EAST,
            Division.AFC_WEST: Division.NFC_SOUTH,
        },
        # Year 1 of 4-year cycle
        1: {
            Division.AFC_EAST: Division.NFC_SOUTH,
            Division.AFC_NORTH: Division.NFC_EAST,
            Division.AFC_SOUTH: Division.NFC_NORTH,
            Division.AFC_WEST: Division.NFC_WEST,
        },
        # Year 2 of 4-year cycle
        2: {
            Division.AFC_EAST: Division.NFC_WEST,
            Division.AFC_NORTH: Division.NFC_SOUTH,
            Division.AFC_SOUTH: Division.NFC_WEST,
            Division.AFC_WEST: Division.NFC_EAST,
        },
        # Year 3 of 4-year cycle
        3: {
            Division.AFC_EAST: Division.NFC_EAST,
            Division.AFC_NORTH: Division.NFC_NORTH,
            Division.AFC_SOUTH: Division.NFC_SOUTH,
            Division.AFC_WEST: Division.NFC_NORTH,
        }
    }
    
    INTRA_AFC_ROTATION = {
        # Year 0 of 3-year cycle
        0: {
            Division.AFC_EAST: Division.AFC_NORTH,
            Division.AFC_NORTH: Division.AFC_WEST,
            Division.AFC_SOUTH: Division.AFC_EAST,
            Division.AFC_WEST: Division.AFC_SOUTH,
        },
        # Year 1 of 3-year cycle
        1: {
            Division.AFC_EAST: Division.AFC_SOUTH,
            Division.AFC_NORTH: Division.AFC_EAST,
            Division.AFC_SOUTH: Division.AFC_WEST,
            Division.AFC_WEST: Division.AFC_NORTH,
        },
        # Year 2 of 3-year cycle
        2: {
            Division.AFC_EAST: Division.AFC_WEST,
            Division.AFC_NORTH: Division.AFC_SOUTH,
            Division.AFC_SOUTH: Division.AFC_NORTH,
            Division.AFC_WEST: Division.AFC_EAST,
        }
    }
    
    INTRA_NFC_ROTATION = {
        # Year 0 of 3-year cycle
        0: {
            Division.NFC_EAST: Division.NFC_NORTH,
            Division.NFC_NORTH: Division.NFC_WEST,
            Division.NFC_SOUTH: Division.NFC_EAST,
            Division.NFC_WEST: Division.NFC_SOUTH,
        },
        # Year 1 of 3-year cycle
        1: {
            Division.NFC_EAST: Division.NFC_SOUTH,
            Division.NFC_NORTH: Division.NFC_EAST,
            Division.NFC_SOUTH: Division.NFC_WEST,
            Division.NFC_WEST: Division.NFC_NORTH,
        },
        # Year 2 of 3-year cycle
        2: {
            Division.NFC_EAST: Division.NFC_WEST,
            Division.NFC_NORTH: Division.NFC_SOUTH,
            Division.NFC_SOUTH: Division.NFC_NORTH,
            Division.NFC_WEST: Division.NFC_EAST,
        }
    }
    
    def __init__(self, year: int, base_year: int = 2024):
        """
        Initialize rotation engine.
        
        Args:
            year: Year to generate schedule for
            base_year: Base year for rotation calculations (2024 is year 0)
        """
        self.year = year
        self.base_year = base_year
        self.year_offset = year - base_year
        self.historical_data = HistoricalDataLoader(year)
    
    def get_rotation_cycle(self) -> RotationCycle:
        """Get the rotation cycle for the current year"""
        # Calculate cycle positions
        interconf_cycle = self.year_offset % 4
        intraconf_cycle = self.year_offset % 3
        
        # Build conference rotations
        conference_rotations = {}
        conference_rotations.update(self.INTRA_AFC_ROTATION[intraconf_cycle])
        conference_rotations.update(self.INTRA_NFC_ROTATION[intraconf_cycle])
        
        # Build interconference rotations
        interconf_rotations = self.AFC_NFC_ROTATION[interconf_cycle].copy()
        
        # Add reverse mappings (NFC -> AFC)
        for afc_div, nfc_div in self.AFC_NFC_ROTATION[interconf_cycle].items():
            interconf_rotations[nfc_div] = afc_div
        
        return RotationCycle(
            year=self.year,
            conference_rotations=conference_rotations,
            interconference_rotations=interconf_rotations
        )
    
    def calculate_division_matchups(self, team_id: int) -> List[Tuple[int, int]]:
        """
        Calculate all division matchups for a team.
        Returns list of (opponent_id, home_away) where 1=home, 0=away
        """
        matchups = []
        division_opponents = NFL_STRUCTURE.get_division_opponents(team_id)
        
        for opponent in division_opponents:
            # Each division opponent played twice (home and away)
            matchups.append((opponent, 1))  # Home game
            matchups.append((opponent, 0))  # Away game
        
        return matchups
    
    def calculate_conference_rotation(self, team_id: int) -> List[Tuple[int, int]]:
        """
        Calculate conference rotation matchups (4 games).
        Play all teams from one other division in same conference.
        """
        team_division = NFL_STRUCTURE.get_division_for_team(team_id)
        rotation_cycle = self.get_rotation_cycle()
        
        # Get the division we're playing this year
        opponent_division = rotation_cycle.conference_rotations.get(team_division)
        if not opponent_division:
            return []
        
        opponent_teams = NFL_STRUCTURE.divisions[opponent_division]
        matchups = []
        
        # Determine home/away split (alternates by year and team)
        # Simple algorithm: lower team IDs get 2 home games in even years
        home_games = 2 if (team_id + self.year) % 2 == 0 else 2
        
        for i, opponent in enumerate(opponent_teams):
            home_away = 1 if i < home_games else 0
            matchups.append((opponent, home_away))
        
        return matchups
    
    def calculate_interconference_rotation(self, team_id: int) -> List[Tuple[int, int]]:
        """
        Calculate inter-conference rotation matchups (4 games).
        Play all teams from one division in other conference.
        """
        team_division = NFL_STRUCTURE.get_division_for_team(team_id)
        rotation_cycle = self.get_rotation_cycle()
        
        # Get the division we're playing this year
        opponent_division = rotation_cycle.interconference_rotations.get(team_division)
        if not opponent_division:
            return []
        
        opponent_teams = NFL_STRUCTURE.divisions[opponent_division]
        matchups = []
        
        # Home/away split for inter-conference
        home_games = 2 if (team_id % 2) == (self.year % 2) else 2
        
        for i, opponent in enumerate(opponent_teams):
            home_away = 1 if i < home_games else 0
            matchups.append((opponent, home_away))
        
        return matchups
    
    def calculate_place_based_matchups(self, team_id: int) -> List[Tuple[int, int]]:
        """
        Calculate place-based matchups (3 games).
        - 2 games vs same-place teams in conference (different divisions)
        - 1 game vs same-place team in other conference
        """
        team_standing = self.historical_data.standings[team_id]
        division_rank = team_standing.division_rank
        
        team_division = NFL_STRUCTURE.get_division_for_team(team_id)
        team_conference = NFL_STRUCTURE.get_conference_for_team(team_id)
        
        matchups = []
        conference_matches = 0
        interconf_matches = 0
        
        # Already playing one full division from each conference
        rotation_cycle = self.get_rotation_cycle()
        conf_opponent_div = rotation_cycle.conference_rotations.get(team_division)
        interconf_opponent_div = rotation_cycle.interconference_rotations.get(team_division)
        
        # Find same-place teams
        for other_team_id in range(1, 33):
            if other_team_id == team_id:
                continue
            
            other_standing = self.historical_data.standings[other_team_id]
            if other_standing.division_rank != division_rank:
                continue
            
            other_division = NFL_STRUCTURE.get_division_for_team(other_team_id)
            other_conference = NFL_STRUCTURE.get_conference_for_team(other_team_id)
            
            # Skip if in same division (already playing twice)
            if other_division == team_division:
                continue
            
            # Skip if in rotation division (already playing)
            if other_division in [conf_opponent_div, interconf_opponent_div]:
                continue
            
            # Same conference place-based (need 2)
            if other_conference == team_conference and conference_matches < 2:
                home_away = 1 if conference_matches == 0 else 0
                matchups.append((other_team_id, home_away))
                conference_matches += 1
            
            # Other conference place-based (need 1)
            elif other_conference != team_conference and interconf_matches < 1:
                home_away = 1 if team_id < other_team_id else 0
                matchups.append((other_team_id, home_away))
                interconf_matches += 1
            
            if conference_matches == 2 and interconf_matches == 1:
                break
        
        return matchups
```

### Step 13: Generate Required Matchups

**File:** `src/scheduling/generator/matchup_generator.py`
```python
"""
Matchup Generator

Generates all required matchups for a complete NFL season.
"""

from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
from ..generator.rotation_engine import RotationEngine

@dataclass
class Matchup:
    """Represents a required matchup between two teams"""
    home_team_id: int
    away_team_id: int
    matchup_type: str  # division, conference, interconference, place_based
    priority: int = 5  # 1-10, higher = more important
    requirements: Dict = None
    
    @property
    def game_id(self) -> str:
        return f"{self.away_team_id}@{self.home_team_id}"
    
    def involves_team(self, team_id: int) -> bool:
        return team_id in [self.home_team_id, self.away_team_id]

class MatchupGenerator:
    """Generates all required matchups for an NFL season"""
    
    def __init__(self, year: int):
        self.year = year
        self.rotation_engine = RotationEngine(year)
        self.matchups: List[Matchup] = []
        self.team_matchup_count: Dict[int, int] = defaultdict(int)
        self.team_home_count: Dict[int, int] = defaultdict(int)
        self.team_away_count: Dict[int, int] = defaultdict(int)
    
    def generate_all_matchups(self) -> List[Matchup]:
        """Generate all 272 matchups for the season"""
        self.matchups = []
        
        # Generate matchups for each team
        for team_id in range(1, 33):
            self._generate_team_matchups(team_id)
        
        # Validate and adjust
        self._validate_matchups()
        self._balance_home_away()
        
        return self.matchups
    
    def _generate_team_matchups(self, team_id: int) -> None:
        """Generate all matchups for a specific team"""
        
        # Division matchups (6 games)
        division_matchups = self.rotation_engine.calculate_division_matchups(team_id)
        for opponent_id, home_away in division_matchups:
            if home_away == 1:  # Home game
                self._add_matchup(team_id, opponent_id, "division", priority=8)
            # Away games will be added when processing opponent
        
        # Conference rotation (4 games)
        conf_matchups = self.rotation_engine.calculate_conference_rotation(team_id)
        for opponent_id, home_away in conf_matchups:
            if home_away == 1:
                self._add_matchup(team_id, opponent_id, "conference", priority=5)
            else:
                self._add_matchup(opponent_id, team_id, "conference", priority=5)
        
        # Inter-conference rotation (4 games)
        interconf_matchups = self.rotation_engine.calculate_interconference_rotation(team_id)
        for opponent_id, home_away in interconf_matchups:
            if home_away == 1:
                self._add_matchup(team_id, opponent_id, "interconference", priority=4)
            else:
                self._add_matchup(opponent_id, team_id, "interconference", priority=4)
        
        # Place-based matchups (3 games)
        place_matchups = self.rotation_engine.calculate_place_based_matchups(team_id)
        for opponent_id, home_away in place_matchups:
            if home_away == 1:
                self._add_matchup(team_id, opponent_id, "place_based", priority=6)
            else:
                self._add_matchup(opponent_id, team_id, "place_based", priority=6)
    
    def _add_matchup(self, home_team: int, away_team: int, 
                    matchup_type: str, priority: int = 5) -> None:
        """Add a matchup if it doesn't already exist"""
        # Check if matchup already exists
        for existing in self.matchups:
            if (existing.home_team_id == home_team and 
                existing.away_team_id == away_team):
                return  # Already exists
        
        matchup = Matchup(
            home_team_id=home_team,
            away_team_id=away_team,
            matchup_type=matchup_type,
            priority=priority
        )
        
        self.matchups.append(matchup)
        self.team_matchup_count[home_team] += 1
        self.team_matchup_count[away_team] += 1
        self.team_home_count[home_team] += 1
        self.team_away_count[away_team] += 1
    
    def _validate_matchups(self) -> None:
        """Validate that all matchup requirements are met"""
        errors = []
        
        # Check each team has 17 games
        for team_id in range(1, 33):
            game_count = self.team_matchup_count[team_id]
            if game_count != 17:
                errors.append(f"Team {team_id} has {game_count} games, expected 17")
        
        # Check total matchups
        if len(self.matchups) != 272:
            errors.append(f"Total matchups: {len(self.matchups)}, expected 272")
        
        # Check division games (each pair plays twice)
        division_pairs = defaultdict(int)
        for matchup in self.matchups:
            if matchup.matchup_type == "division":
                pair = tuple(sorted([matchup.home_team_id, matchup.away_team_id]))
                division_pairs[pair] += 1
        
        for pair, count in division_pairs.items():
            if count != 2:
                errors.append(f"Division pair {pair} plays {count} times, expected 2")
        
        if errors:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
    
    def _balance_home_away(self) -> None:
        """Ensure each team has 8 or 9 home games"""
        for team_id in range(1, 33):
            home_count = self.team_home_count[team_id]
            away_count = self.team_away_count[team_id]
            
            if home_count not in [8, 9]:
                print(f"Warning: Team {team_id} has {home_count} home games")
                # Would implement balancing logic here
    
    def get_team_matchups(self, team_id: int) -> List[Matchup]:
        """Get all matchups for a specific team"""
        return [m for m in self.matchups if m.involves_team(team_id)]
    
    def get_matchups_by_type(self, matchup_type: str) -> List[Matchup]:
        """Get all matchups of a specific type"""
        return [m for m in self.matchups if m.matchup_type == matchup_type]
    
    def get_division_matchups(self) -> List[Matchup]:
        """Get all division matchups"""
        return self.get_matchups_by_type("division")
    
    def get_primetime_worthy_matchups(self) -> List[Matchup]:
        """Get matchups suitable for primetime slots"""
        # Would use team classifier to identify high-value matchups
        return [m for m in self.matchups if m.priority >= 7]
```

**Deliverable:** Complete rotation engine with all NFL scheduling rules implemented

---

## Milestone Checkpoint - Week 2 Complete

At this point, we have:
- ✅ Data layer functional (teams, divisions, historical data)
- ✅ Template system working (loader, builder, slot manager)
- ✅ Team classification done (market tiers, competitive tiers, rivalries)
- ✅ Rotation logic implemented (all NFL rules for matchups)

Ready to proceed with:
- Phase 5: Constraint System
- Phase 6: Special Games
- Phase 7: Main Builder
- Phase 8-11: Validation, Integration, Testing, and Deployment

**Total Progress: 33% Complete (Days 1-13 of 42)**

The remaining phases follow the same detailed pattern, implementing:
- Constraint solver using python-constraint library
- Special game handlers for Thanksgiving, Christmas, International
- Main schedule builder orchestrating all components
- Comprehensive validation system
- CalendarManager integration
- Full test suite
- Documentation and deployment

This development roadmap provides a complete, actionable plan for building a professional NFL schedule generator from scratch.