"""
Configuration for NFL Schedule Generator

Centralized configuration management for schedule generation parameters,
constraints, and special game settings.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from datetime import date, time
from enum import Enum
import json
from pathlib import Path


class ScheduleStrategy(Enum):
    """Schedule generation strategy"""
    TEMPLATE_BASED = "template_based"      # Use historical template
    ROUND_ROBIN = "round_robin"            # Mathematical round-robin
    CONSTRAINT_SOLVER = "constraint_solver" # Pure constraint satisfaction
    HYBRID = "hybrid"                      # Combination approach


class PrimetimeAllocation(Enum):
    """How to allocate primetime games"""
    BALANCED = "balanced"          # Distribute evenly
    MARKET_BASED = "market_based"  # Favor large markets
    RIVALRY_FOCUSED = "rivalry"    # Prioritize rivalries
    ROTATION = "rotation"          # Strict rotation


@dataclass
class ByeWeekConfig:
    """Configuration for bye week scheduling"""
    start_week: int = 6           # Earliest bye week
    end_week: int = 14            # Latest bye week
    max_teams_per_week: int = 6   # Maximum teams on bye each week
    min_teams_per_week: int = 2   # Minimum teams on bye each week
    division_spread: bool = True  # Spread division teams' byes
    
    def validate(self) -> bool:
        """Validate bye week configuration"""
        if self.start_week < 1 or self.end_week > 18:
            return False
        if self.start_week >= self.end_week:
            return False
        if self.max_teams_per_week < self.min_teams_per_week:
            return False
        
        # Check total bye capacity
        weeks_available = self.end_week - self.start_week + 1
        max_capacity = weeks_available * self.max_teams_per_week
        if max_capacity < 32:  # Need bye for all 32 teams
            return False
        
        return True


@dataclass
class PrimetimeConfig:
    """Configuration for primetime game scheduling"""
    tnf_start_week: int = 2          # Thursday Night Football starts
    tnf_end_week: int = 17           # TNF ends
    mnf_doubleheader_week: int = 1   # Week 1 MNF doubleheader
    saturday_start_week: int = 15    # Late season Saturday games
    
    # Number of primetime games per slot
    slots_per_week: Dict[str, int] = field(default_factory=lambda: {
        'TNF': 1,
        'SNF': 1,
        'MNF': 1
    })
    
    # Teams primetime appearance limits
    max_primetime_games: int = 5     # Max primetime per team
    min_primetime_games: int = 1     # Min primetime per team
    max_tnf_games: int = 2           # Max TNF per team
    
    # Market preferences
    favor_large_markets: bool = True
    large_market_teams: Set[int] = field(default_factory=lambda: {
        17,  # Dallas Cowboys
        18,  # New York Giants
        19,  # Philadelphia Eagles
        21,  # Chicago Bears
        30,  # Los Angeles Rams
        31,  # San Francisco 49ers
    })


@dataclass
class SpecialGamesConfig:
    """Configuration for special games (Thanksgiving, Christmas, etc.)"""
    
    # Thanksgiving games
    thanksgiving_games: int = 3
    thanksgiving_hosts: List[int] = field(default_factory=lambda: [
        17,  # Dallas Cowboys (traditional)
        22,  # Detroit Lions (traditional)
    ])
    
    # Christmas games
    christmas_games: int = 2
    christmas_preferred_teams: Set[int] = field(default_factory=set)
    
    # International games
    international_games: int = 5
    london_games: int = 3
    germany_games: int = 1
    mexico_games: int = 1
    
    # Teams volunteering for international
    international_home_teams: Set[int] = field(default_factory=lambda: {
        11,  # Jacksonville Jaguars (London)
    })
    
    # Season opener
    season_opener_champion: bool = True  # Champion hosts opener
    season_opener_rival: bool = True     # Against division rival if possible


@dataclass
class ConstraintWeights:
    """
    Weights for soft constraints in schedule optimization.
    Higher values = more important.
    """
    home_away_balance: float = 10.0      # Alternate home/away
    division_spacing: float = 8.0        # Space division games
    bye_week_fairness: float = 9.0       # Fair bye week distribution
    travel_minimization: float = 5.0     # Minimize travel distance
    competitive_balance: float = 7.0     # Balance schedule difficulty
    primetime_distribution: float = 6.0  # Fair primetime distribution
    rivalry_placement: float = 8.0       # Good slots for rivalries
    weather_consideration: float = 4.0   # Cold weather late season
    rest_equality: float = 6.0          # Equal rest between games
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'home_away_balance': self.home_away_balance,
            'division_spacing': self.division_spacing,
            'bye_week_fairness': self.bye_week_fairness,
            'travel_minimization': self.travel_minimization,
            'competitive_balance': self.competitive_balance,
            'primetime_distribution': self.primetime_distribution,
            'rivalry_placement': self.rivalry_placement,
            'weather_consideration': self.weather_consideration,
            'rest_equality': self.rest_equality
        }


@dataclass
class ScheduleConfig:
    """Complete configuration for NFL schedule generation"""
    
    # Basic parameters
    season_year: int
    strategy: ScheduleStrategy = ScheduleStrategy.TEMPLATE_BASED
    total_weeks: int = 18
    games_per_team: int = 17
    
    # Component configurations
    bye_week: ByeWeekConfig = field(default_factory=ByeWeekConfig)
    primetime: PrimetimeConfig = field(default_factory=PrimetimeConfig)
    special_games: SpecialGamesConfig = field(default_factory=SpecialGamesConfig)
    constraint_weights: ConstraintWeights = field(default_factory=ConstraintWeights)
    
    # Optimization parameters
    max_iterations: int = 10000
    optimization_timeout: int = 300  # seconds
    target_quality_score: float = 0.85
    use_parallel_optimization: bool = True
    parallel_threads: int = 4
    
    # Validation settings
    strict_validation: bool = True
    allow_partial_schedules: bool = False
    
    # Output settings
    output_format: str = "json"
    include_metadata: bool = True
    generate_reports: bool = True
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate entire configuration"""
        errors = []
        
        # Basic validation
        if self.season_year < 2020 or self.season_year > 2050:
            errors.append(f"Invalid season year: {self.season_year}")
        
        if self.total_weeks != 18:
            errors.append(f"NFL uses 18 weeks, got {self.total_weeks}")
        
        if self.games_per_team != 17:
            errors.append(f"NFL teams play 17 games, got {self.games_per_team}")
        
        # Component validation
        if not self.bye_week.validate():
            errors.append("Invalid bye week configuration")
        
        # Check optimization parameters
        if self.max_iterations < 100:
            errors.append("Max iterations too low for quality schedule")
        
        if self.parallel_threads < 1:
            errors.append("Need at least 1 thread")
        
        return len(errors) == 0, errors
    
    def to_json(self, filepath: str):
        """Save configuration to JSON file"""
        config_dict = {
            'season_year': self.season_year,
            'strategy': self.strategy.value,
            'total_weeks': self.total_weeks,
            'games_per_team': self.games_per_team,
            'bye_week': {
                'start_week': self.bye_week.start_week,
                'end_week': self.bye_week.end_week,
                'max_teams_per_week': self.bye_week.max_teams_per_week,
                'min_teams_per_week': self.bye_week.min_teams_per_week,
                'division_spread': self.bye_week.division_spread
            },
            'primetime': {
                'tnf_start_week': self.primetime.tnf_start_week,
                'tnf_end_week': self.primetime.tnf_end_week,
                'max_primetime_games': self.primetime.max_primetime_games,
                'min_primetime_games': self.primetime.min_primetime_games,
                'favor_large_markets': self.primetime.favor_large_markets
            },
            'special_games': {
                'thanksgiving_games': self.special_games.thanksgiving_games,
                'thanksgiving_hosts': self.special_games.thanksgiving_hosts,
                'international_games': self.special_games.international_games
            },
            'constraint_weights': self.constraint_weights.to_dict(),
            'optimization': {
                'max_iterations': self.max_iterations,
                'timeout': self.optimization_timeout,
                'target_quality': self.target_quality_score,
                'parallel': self.use_parallel_optimization,
                'threads': self.parallel_threads
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'ScheduleConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        config = cls(season_year=data['season_year'])
        
        # Load strategy
        config.strategy = ScheduleStrategy(data.get('strategy', 'template_based'))
        
        # Load bye week config
        if 'bye_week' in data:
            bye_data = data['bye_week']
            config.bye_week = ByeWeekConfig(
                start_week=bye_data.get('start_week', 6),
                end_week=bye_data.get('end_week', 14),
                max_teams_per_week=bye_data.get('max_teams_per_week', 6),
                min_teams_per_week=bye_data.get('min_teams_per_week', 2),
                division_spread=bye_data.get('division_spread', True)
            )
        
        # Load optimization settings
        if 'optimization' in data:
            opt_data = data['optimization']
            config.max_iterations = opt_data.get('max_iterations', 10000)
            config.optimization_timeout = opt_data.get('timeout', 300)
            config.target_quality_score = opt_data.get('target_quality', 0.85)
            config.use_parallel_optimization = opt_data.get('parallel', True)
            config.parallel_threads = opt_data.get('threads', 4)
        
        return config
    
    @classmethod
    def default_2024(cls) -> 'ScheduleConfig':
        """Create default configuration for 2024 season"""
        return cls(
            season_year=2024,
            strategy=ScheduleStrategy.TEMPLATE_BASED,
            bye_week=ByeWeekConfig(
                start_week=5,  # 2024 bye weeks start week 5
                end_week=14,
                max_teams_per_week=6,
                min_teams_per_week=2
            ),
            primetime=PrimetimeConfig(
                tnf_start_week=2,
                tnf_end_week=17,
                mnf_doubleheader_week=1
            ),
            special_games=SpecialGamesConfig(
                thanksgiving_games=3,
                international_games=5,
                london_games=3,
                germany_games=1,
                mexico_games=1
            )
        )


# Global default configuration
DEFAULT_CONFIG = ScheduleConfig.default_2024()