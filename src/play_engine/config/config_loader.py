"""
Configuration loader for play engine parameters

Centralizes all magic numbers and balance parameters for designer modification
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class PlayEngineConfig:
    """Singleton configuration loader for play engine parameters"""
    
    _instance = None
    _configs = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlayEngineConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config_dir = Path(__file__).parent
            self.initialized = True
            self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        config_files = {
            'run_play': 'run_play_config.json',
            'pass_play': 'pass_play_config.json'
        }
        
        for config_name, filename in config_files.items():
            config_path = self.config_dir / filename
            try:
                with open(config_path, 'r') as f:
                    self._configs[config_name] = json.load(f)
                print(f"Loaded {config_name} configuration from {filename}")
            except FileNotFoundError:
                print(f"Warning: Config file {filename} not found, using defaults")
                self._configs[config_name] = {}
            except json.JSONDecodeError as e:
                print(f"Error parsing {filename}: {e}")
                self._configs[config_name] = {}
    
    def get_run_play_config(self) -> Dict[str, Any]:
        """Get run play configuration"""
        return self._configs.get('run_play', {})
    
    def get_pass_play_config(self) -> Dict[str, Any]:
        """Get pass play configuration"""  
        return self._configs.get('pass_play', {})
    
    def get_formation_matchup(self, config_type: str, offensive_formation: str, 
                            defensive_formation: str) -> Optional[Dict[str, Any]]:
        """
        Get formation matchup parameters
        
        Args:
            config_type: 'run_play' or 'pass_play'
            offensive_formation: Offensive formation name
            defensive_formation: Defensive formation name
            
        Returns:
            Matchup parameters or None if not found
        """
        config = self._configs.get(config_type, {})
        formation_matchups = config.get('formation_matchups', {})
        matchups = formation_matchups.get('matchups', {})
        
        # Try to find specific matchup
        if offensive_formation in matchups:
            off_matchups = matchups[offensive_formation]
            if defensive_formation in off_matchups:
                return off_matchups[defensive_formation]
        
        # Fall back to default
        return formation_matchups.get('default_matchup')
    
    def get_player_attribute_config(self, config_type: str) -> Dict[str, Any]:
        """Get player attribute configuration"""
        config = self._configs.get(config_type, {})
        return config.get('player_attributes', {})
    
    def get_rating_threshold(self, config_type: str, threshold_name: str) -> int:
        """Get a specific rating threshold"""
        attr_config = self.get_player_attribute_config(config_type)
        thresholds = attr_config.get('rating_thresholds', {})
        
        # Default values if config not found
        defaults = {'elite': 90, 'very_good': 85, 'good': 80, 'average': 75, 'below_average': 65, 'poor': 60}
        return thresholds.get(threshold_name, defaults.get(threshold_name, 75))
    
    def get_modifier_value(self, config_type: str, category: str, modifier_name: str) -> float:
        """Get a specific modifier value"""
        attr_config = self.get_player_attribute_config(config_type)
        category_config = attr_config.get(category, {})
        return category_config.get(modifier_name, 1.0)
    
    def get_play_mechanics_config(self, config_type: str) -> Dict[str, Any]:
        """Get play mechanics configuration"""
        config = self._configs.get(config_type, {})
        return config.get('play_mechanics', {})
    
    def get_timing_config(self, config_type: str) -> Dict[str, Any]:
        """Get timing configuration"""
        config = self._configs.get(config_type, {})
        return config.get('play_timing', {})
    
    def get_statistical_attribution_config(self, config_type: str) -> Dict[str, Any]:
        """Get statistical attribution configuration"""
        config = self._configs.get(config_type, {})
        return config.get('statistical_attribution', {})
    
    def get_variance_ranges_config(self, config_type: str) -> Dict[str, Any]:
        """Get variance ranges configuration"""
        config = self._configs.get(config_type, {})
        return config.get('variance_ranges', {})
    
    def reload_configs(self):
        """Reload all configuration files (useful for runtime config changes)"""
        self._configs.clear()
        self._load_all_configs()


# Global configuration instance
config = PlayEngineConfig()


# Convenience functions for common config access
def get_run_formation_matchup(offensive_formation: str, defensive_formation: str) -> Optional[Dict[str, Any]]:
    """Get run play formation matchup parameters"""
    return config.get_formation_matchup('run_play', offensive_formation, defensive_formation)


def get_pass_formation_matchup(offensive_formation: str, defensive_formation: str) -> Optional[Dict[str, Any]]:
    """Get pass play formation matchup parameters"""
    return config.get_formation_matchup('pass_play', offensive_formation, defensive_formation)


def get_run_player_threshold(threshold_name: str) -> int:
    """Get run play player rating threshold"""
    return config.get_rating_threshold('run_play', threshold_name)


def get_pass_player_threshold(threshold_name: str) -> int:
    """Get pass play player rating threshold"""
    return config.get_rating_threshold('pass_play', threshold_name)


def get_run_modifier(category: str, modifier_name: str) -> float:
    """Get run play modifier value"""
    return config.get_modifier_value('run_play', category, modifier_name)


def get_pass_modifier(category: str, modifier_name: str) -> float:
    """Get pass play modifier value"""
    return config.get_modifier_value('pass_play', category, modifier_name)