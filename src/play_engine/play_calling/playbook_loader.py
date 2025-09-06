"""
Playbook Loader System - Manages playbook configurations and situational play sets

Loads JSON-based playbook configurations that define available plays for different
game situations, formations, and down/distance combinations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import json
from pathlib import Path
from enum import Enum

from ..play_types.offensive_types import OffensivePlayType
from ..play_types.defensive_types import DefensivePlayType
from ..mechanics.formations import OffensiveFormation, DefensiveFormation


class SituationType(Enum):
    """Different situation categories for playbook organization"""
    FIRST_DOWN = "first_down"
    SECOND_SHORT = "second_short"        # 2nd & 1-3
    SECOND_MEDIUM = "second_medium"      # 2nd & 4-7
    SECOND_LONG = "second_long"          # 2nd & 8+
    THIRD_SHORT = "third_short"          # 3rd & 1-3
    THIRD_MEDIUM = "third_medium"        # 3rd & 4-7
    THIRD_LONG = "third_long"            # 3rd & 8+
    FOURTH_DOWN = "fourth_down"
    RED_ZONE = "red_zone"                # Inside 20
    GOAL_LINE = "goal_line"              # Inside 5
    TWO_MINUTE = "two_minute"            # Under 2:00
    HAIL_MARY = "hail_mary"              # Last play desperation


@dataclass
class PlayOption:
    """A single play option with metadata"""
    play_type: str                       # OffensivePlayType or DefensivePlayType
    formation: str                       # Formation type
    concept: str                         # Play concept name
    weight: float = 1.0                  # Selection weight (higher = more likely)
    success_rate: float = 0.5           # Historical success rate
    risk_level: float = 0.5             # Risk level (0=safe, 1=risky)
    personnel_package: Optional[str] = None  # Personnel requirement
    conditions: Optional[Dict[str, Any]] = None  # Special conditions
    
    def __post_init__(self):
        """Initialize default conditions if not provided"""
        if self.conditions is None:
            self.conditions = {}


@dataclass
class SituationalPlaySet:
    """Collection of plays available for a specific situation"""
    situation: str                       # Situation identifier
    offensive_plays: List[PlayOption] = field(default_factory=list)
    defensive_plays: List[PlayOption] = field(default_factory=list)
    description: str = ""               # Human-readable description
    
    def get_offensive_options(self, filters: Optional[Dict[str, Any]] = None) -> List[PlayOption]:
        """Get filtered offensive play options"""
        if not filters:
            return self.offensive_plays
        
        filtered_plays = []
        for play in self.offensive_plays:
            if self._matches_filters(play, filters):
                filtered_plays.append(play)
        
        return filtered_plays
    
    def get_defensive_options(self, filters: Optional[Dict[str, Any]] = None) -> List[PlayOption]:
        """Get filtered defensive play options"""
        if not filters:
            return self.defensive_plays
        
        filtered_plays = []
        for play in self.defensive_plays:
            if self._matches_filters(play, filters):
                filtered_plays.append(play)
        
        return filtered_plays
    
    def _matches_filters(self, play: PlayOption, filters: Dict[str, Any]) -> bool:
        """Check if play matches the given filters"""
        for key, value in filters.items():
            if key == 'formation':
                if play.formation != value:
                    return False
            elif key == 'max_risk':
                if play.risk_level > value:
                    return False
            elif key == 'min_success_rate':
                if play.success_rate < value:
                    return False
            elif key in play.conditions:
                if play.conditions[key] != value:
                    return False
        
        return True


@dataclass
class Playbook:
    """Complete playbook with situational play sets"""
    name: str
    description: str = ""
    situational_sets: Dict[str, SituationalPlaySet] = field(default_factory=dict)
    
    def get_situation_plays(self, situation_type: str) -> Optional[SituationalPlaySet]:
        """Get plays for a specific situation"""
        return self.situational_sets.get(situation_type)
    
    def add_situation_set(self, situation_set: SituationalPlaySet):
        """Add a situational play set to the playbook"""
        self.situational_sets[situation_set.situation] = situation_set
    
    def list_situations(self) -> List[str]:
        """Get list of available situation types"""
        return list(self.situational_sets.keys())


class PlaybookLoader:
    """Loads and manages playbook configurations"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize playbook loader
        
        Args:
            config_dir: Directory containing playbook JSON files
        """
        if config_dir is None:
            # Default to src/config/playbooks/ directory
            config_dir = Path(__file__).parent.parent.parent / "config" / "playbooks"
        
        self.config_dir = Path(config_dir)
        self._playbook_cache: Dict[str, Playbook] = {}
    
    def load_playbook(self, playbook_name: str) -> Playbook:
        """
        Load playbook from JSON file
        
        Args:
            playbook_name: Name of playbook file (without .json extension)
            
        Returns:
            Playbook instance
        """
        # Check cache first
        if playbook_name in self._playbook_cache:
            return self._playbook_cache[playbook_name]
        
        playbook_file = self.config_dir / f"{playbook_name}.json"
        
        if not playbook_file.exists():
            # Return a basic default playbook if file not found
            return self._create_default_playbook(playbook_name)
        
        with open(playbook_file, 'r') as f:
            data = json.load(f)
        
        playbook = self._parse_playbook_data(data)
        
        # Cache the loaded playbook
        self._playbook_cache[playbook_name] = playbook
        
        return playbook
    
    def _parse_playbook_data(self, data: Dict[str, Any]) -> Playbook:
        """Parse JSON data into Playbook object"""
        playbook = Playbook(
            name=data['name'],
            description=data.get('description', '')
        )
        
        # Parse situational sets
        situations_data = data.get('situations', {})
        for situation_name, situation_data in situations_data.items():
            situation_set = self._parse_situation_set(situation_name, situation_data)
            playbook.add_situation_set(situation_set)
        
        return playbook
    
    def _parse_situation_set(self, situation_name: str, data: Dict[str, Any]) -> SituationalPlaySet:
        """Parse situational play set data"""
        situation_set = SituationalPlaySet(
            situation=situation_name,
            description=data.get('description', '')
        )
        
        # Parse offensive plays
        offensive_data = data.get('offensive_plays', [])
        for play_data in offensive_data:
            play_option = self._parse_play_option(play_data)
            situation_set.offensive_plays.append(play_option)
        
        # Parse defensive plays
        defensive_data = data.get('defensive_plays', [])
        for play_data in defensive_data:
            play_option = self._parse_play_option(play_data)
            situation_set.defensive_plays.append(play_option)
        
        return situation_set
    
    def _parse_play_option(self, data: Dict[str, Any]) -> PlayOption:
        """Parse individual play option"""
        return PlayOption(
            play_type=data['play_type'],
            formation=data['formation'],
            concept=data['concept'],
            weight=data.get('weight', 1.0),
            success_rate=data.get('success_rate', 0.5),
            risk_level=data.get('risk_level', 0.5),
            personnel_package=data.get('personnel_package'),
            conditions=data.get('conditions', {})
        )
    
    def _create_default_playbook(self, playbook_name: str) -> Playbook:
        """Create a basic default playbook when file not found"""
        playbook = Playbook(
            name=playbook_name,
            description=f"Default playbook for {playbook_name}"
        )
        
        # Add basic situational sets with common plays
        self._add_default_situations(playbook)
        
        return playbook
    
    def _add_default_situations(self, playbook: Playbook):
        """Add default situational play sets"""
        # First down plays
        first_down = SituationalPlaySet(
            situation="first_down",
            description="Standard first down plays"
        )
        first_down.offensive_plays.extend([
            PlayOption(
                play_type=OffensivePlayType.RUN,
                formation=OffensiveFormation.I_FORMATION,
                concept="power",
                weight=0.6
            ),
            PlayOption(
                play_type=OffensivePlayType.PASS,
                formation=OffensiveFormation.SHOTGUN,
                concept="slants",
                weight=0.4
            )
        ])
        first_down.defensive_plays.extend([
            PlayOption(
                play_type=DefensivePlayType.COVER_2,
                formation=DefensiveFormation.FOUR_THREE,
                concept="base_defense",
                weight=1.0
            )
        ])
        playbook.add_situation_set(first_down)
        
        # Third and long
        third_long = SituationalPlaySet(
            situation="third_long",
            description="Third down and long yardage"
        )
        third_long.offensive_plays.extend([
            PlayOption(
                play_type=OffensivePlayType.PASS,
                formation=OffensiveFormation.SHOTGUN,
                concept="comeback",
                weight=0.7
            ),
            PlayOption(
                play_type=OffensivePlayType.PASS,
                formation=OffensiveFormation.FOUR_WIDE,
                concept="crossing_routes",
                weight=0.3
            )
        ])
        third_long.defensive_plays.extend([
            PlayOption(
                play_type=DefensivePlayType.COVER_3,
                formation=DefensiveFormation.NICKEL,
                concept="pass_rush",
                weight=1.0
            )
        ])
        playbook.add_situation_set(third_long)
        
        # Red zone
        red_zone = SituationalPlaySet(
            situation="red_zone",
            description="Red zone plays"
        )
        red_zone.offensive_plays.extend([
            PlayOption(
                play_type=OffensivePlayType.RUN,
                formation=OffensiveFormation.I_FORMATION,
                concept="power",
                weight=0.5
            ),
            PlayOption(
                play_type=OffensivePlayType.PASS,
                formation=OffensiveFormation.SHOTGUN,
                concept="fade",
                weight=0.5
            )
        ])
        red_zone.defensive_plays.extend([
            PlayOption(
                play_type=DefensivePlayType.COVER_2,
                formation=DefensiveFormation.FOUR_THREE,
                concept="goal_line",
                weight=1.0
            )
        ])
        playbook.add_situation_set(red_zone)
    
    def list_available_playbooks(self) -> List[str]:
        """Get list of available playbook files"""
        if not self.config_dir.exists():
            return []
        
        playbook_files = self.config_dir.glob("*.json")
        return [f.stem for f in playbook_files]
    
    def save_playbook(self, playbook: Playbook, filename: str = None):
        """
        Save playbook to JSON file
        
        Args:
            playbook: Playbook to save
            filename: Optional filename override
        """
        filename = filename or f"{playbook.name.lower().replace(' ', '_')}.json"
        playbook_file = self.config_dir / filename
        
        # Create directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert playbook to JSON-serializable format
        data = {
            'name': playbook.name,
            'description': playbook.description,
            'situations': {}
        }
        
        for situation_name, situation_set in playbook.situational_sets.items():
            data['situations'][situation_name] = {
                'description': situation_set.description,
                'offensive_plays': [
                    {
                        'play_type': play.play_type,
                        'formation': play.formation,
                        'concept': play.concept,
                        'weight': play.weight,
                        'success_rate': play.success_rate,
                        'risk_level': play.risk_level,
                        'personnel_package': play.personnel_package,
                        'conditions': play.conditions
                    }
                    for play in situation_set.offensive_plays
                ],
                'defensive_plays': [
                    {
                        'play_type': play.play_type,
                        'formation': play.formation,
                        'concept': play.concept,
                        'weight': play.weight,
                        'success_rate': play.success_rate,
                        'risk_level': play.risk_level,
                        'personnel_package': play.personnel_package,
                        'conditions': play.conditions
                    }
                    for play in situation_set.defensive_plays
                ]
            }
        
        with open(playbook_file, 'w') as f:
            json.dump(data, f, indent=2)


class SituationMapper:
    """Maps game situations to playbook situation types"""
    
    @staticmethod
    def get_situation_type(down: int, yards_to_go: int, field_position: int, 
                          time_remaining: Optional[int] = None) -> str:
        """
        Map game state to situation type for playbook lookup
        
        Args:
            down: Current down (1-4)
            yards_to_go: Yards needed for first down
            field_position: Field position (0-100)
            time_remaining: Optional time remaining in seconds
            
        Returns:
            Situation type string for playbook lookup
        """
        # Check special situations first
        if time_remaining and time_remaining <= 120:  # 2:00 remaining
            return SituationType.TWO_MINUTE.value
        
        if field_position >= 95:  # Goal line (5 yards from endzone)
            return SituationType.GOAL_LINE.value
        
        if field_position >= 80:  # Red zone
            return SituationType.RED_ZONE.value
        
        # Down and distance based situations
        if down == 1:
            return SituationType.FIRST_DOWN.value
        elif down == 2:
            if yards_to_go <= 3:
                return SituationType.SECOND_SHORT.value
            elif yards_to_go <= 7:
                return SituationType.SECOND_MEDIUM.value
            else:
                return SituationType.SECOND_LONG.value
        elif down == 3:
            if yards_to_go <= 3:
                return SituationType.THIRD_SHORT.value
            elif yards_to_go <= 7:
                return SituationType.THIRD_MEDIUM.value
            else:
                return SituationType.THIRD_LONG.value
        elif down == 4:
            return SituationType.FOURTH_DOWN.value
        
        # Default fallback
        return SituationType.FIRST_DOWN.value