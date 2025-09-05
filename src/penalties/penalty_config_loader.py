"""
Penalty Configuration Loader

Loads and manages JSON-based penalty configuration files for designer customization.
Provides easy access to penalty rates, discipline effects, situational modifiers, and descriptions.
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PenaltyConfig:
    """Container for all penalty configuration data"""
    base_rates: Dict[str, Any]
    discipline_effects: Dict[str, Any]
    situational_modifiers: Dict[str, Any]
    penalty_descriptions: Dict[str, Any]
    home_field_settings: Dict[str, Any]


class PenaltyConfigLoader:
    """Loads and manages penalty configuration from JSON files"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize penalty configuration loader
        
        Args:
            config_dir: Directory containing penalty config files. 
                       Defaults to src/config/penalties/
        """
        if config_dir is None:
            # Default to config directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(current_dir, '..', 'config', 'penalties')
        
        self.config_dir = os.path.abspath(config_dir)
        self._config_cache = None
        self._validate_config_directory()
    
    def _validate_config_directory(self):
        """Ensure configuration directory and files exist"""
        if not os.path.exists(self.config_dir):
            raise FileNotFoundError(f"Penalty configuration directory not found: {self.config_dir}")
        
        required_files = [
            'penalty_rates.json',
            'discipline_effects.json', 
            'situational_modifiers.json',
            'penalty_descriptions.json',
            'home_field_settings.json'
        ]
        
        for filename in required_files:
            filepath = os.path.join(self.config_dir, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Required penalty config file not found: {filepath}")
    
    def _load_json_file(self, filename: str) -> Dict[str, Any]:
        """Load and parse a JSON configuration file"""
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filename}: {e}")
        except Exception as e:
            raise IOError(f"Error reading {filename}: {e}")
    
    def load_config(self, force_reload: bool = False) -> PenaltyConfig:
        """
        Load all penalty configuration files
        
        Args:
            force_reload: If True, reload from files even if cached
            
        Returns:
            PenaltyConfig object containing all configuration data
        """
        if self._config_cache is not None and not force_reload:
            return self._config_cache
        
        # Load all configuration files
        base_rates = self._load_json_file('penalty_rates.json')
        discipline_effects = self._load_json_file('discipline_effects.json')
        situational_modifiers = self._load_json_file('situational_modifiers.json')
        penalty_descriptions = self._load_json_file('penalty_descriptions.json')
        home_field_settings = self._load_json_file('home_field_settings.json')
        
        # Create configuration object
        config = PenaltyConfig(
            base_rates=base_rates,
            discipline_effects=discipline_effects,
            situational_modifiers=situational_modifiers,
            penalty_descriptions=penalty_descriptions,
            home_field_settings=home_field_settings
        )
        
        # Cache for performance
        self._config_cache = config
        return config
    
    def get_penalty_base_rate(self, penalty_type: str) -> float:
        """Get base rate for a specific penalty type"""
        config = self.load_config()
        penalty_info = config.base_rates.get('base_rates', {}).get(penalty_type)
        if penalty_info is None:
            raise ValueError(f"Unknown penalty type: {penalty_type}")
        return penalty_info.get('rate', 0.0)
    
    def get_penalty_yardage(self, penalty_type: str) -> int:
        """Get yardage penalty for a specific penalty type"""
        config = self.load_config()
        penalty_info = config.base_rates.get('base_rates', {}).get(penalty_type)
        if penalty_info is None:
            raise ValueError(f"Unknown penalty type: {penalty_type}")
        return penalty_info.get('yard_penalty', 0)
    
    def is_automatic_first_down(self, penalty_type: str) -> bool:
        """Check if penalty results in automatic first down"""
        config = self.load_config()
        penalty_info = config.base_rates.get('base_rates', {}).get(penalty_type)
        if penalty_info is None:
            return False
        return penalty_info.get('automatic_first_down', False)
    
    def does_negate_play(self, penalty_type: str) -> bool:
        """Check if penalty negates the play result"""
        config = self.load_config()
        penalty_info = config.base_rates.get('base_rates', {}).get(penalty_type)
        if penalty_info is None:
            return False
        return penalty_info.get('negates_play', False)
    
    def get_penalty_timing(self, penalty_type: str) -> str:
        """Get when the penalty occurs (pre_snap, during_play, post_play)"""
        config = self.load_config()
        penalty_info = config.base_rates.get('base_rates', {}).get(penalty_type)
        if penalty_info is None:
            return 'during_play'
        return penalty_info.get('timing', 'during_play')
    
    def get_discipline_modifier(self, discipline_rating: int) -> float:
        """Get penalty modifier based on player discipline rating"""
        config = self.load_config()
        modifiers = config.discipline_effects.get('discipline_modifiers', {})
        
        # Find appropriate modifier based on discipline rating
        for category, info in modifiers.items():
            if discipline_rating >= info.get('threshold', 0):
                return info.get('modifier', 1.0)
        
        # Default to worst discipline modifier
        return 1.8
    
    def get_home_field_modifier(self, is_home_team: bool) -> float:
        """Get home field advantage modifier for penalties"""
        if not is_home_team:
            return 1.0
        
        config = self.load_config()
        home_field = config.home_field_settings.get('home_field_advantage', {})
        
        if not home_field.get('enabled', True):
            return 1.0
        
        return home_field.get('overall_modifier', 0.85)
    
    def get_situational_modifier(self, penalty_type: str, down: int, distance: int, field_position: int) -> float:
        """
        Get situational modifier for penalty based on game state
        
        Args:
            penalty_type: Type of penalty
            down: Current down (1-4)
            distance: Yards to go
            field_position: Yards from own goal line (0-100)
            
        Returns:
            Modifier to apply to base penalty rate
        """
        config = self.load_config()
        modifiers = config.situational_modifiers
        
        total_modifier = 1.0
        
        # Check field position modifiers
        field_mods = modifiers.get('field_position_modifiers', {})
        for situation, info in field_mods.items():
            pos_range = info.get('field_position_range', [0, 100])
            if pos_range[0] <= field_position <= pos_range[1]:
                penalty_mod = info.get('modifiers', {}).get(penalty_type, 1.0)
                total_modifier *= penalty_mod
        
        # Check down and distance modifiers  
        dd_mods = modifiers.get('down_and_distance_modifiers', {})
        for situation, info in dd_mods.items():
            conditions = info.get('conditions', {})
            
            # Check if current situation matches conditions
            matches = True
            if 'down' in conditions and conditions['down'] != down:
                matches = False
            if 'distance_min' in conditions and distance < conditions['distance_min']:
                matches = False
            if 'distance_max' in conditions and distance > conditions['distance_max']:
                matches = False
            if 'field_position_min' in conditions and field_position < conditions['field_position_min']:
                matches = False
            
            if matches:
                penalty_mod = info.get('modifiers', {}).get(penalty_type, 1.0)
                total_modifier *= penalty_mod
        
        return total_modifier
    
    def get_penalty_contexts(self, penalty_type: str) -> Dict[str, Any]:
        """Get contextual information for penalty attribution"""
        config = self.load_config()
        contexts = config.penalty_descriptions.get('penalty_contexts', {})
        return contexts.get(penalty_type, {})
    
    def get_available_penalty_types(self) -> list:
        """Get list of all configured penalty types"""
        config = self.load_config()
        return list(config.base_rates.get('base_rates', {}).keys())
    
    def reload_config(self):
        """Force reload configuration from files (useful for testing/development)"""
        self._config_cache = None
        return self.load_config()


# Global configuration loader instance
_config_loader = None

def get_penalty_config() -> PenaltyConfigLoader:
    """Get global penalty configuration loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = PenaltyConfigLoader()
    return _config_loader