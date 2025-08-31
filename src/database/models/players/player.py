from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum
import random


class InjuryStatus(Enum):
    HEALTHY = "healthy"
    DAY_TO_DAY = "day_to_day"
    QUESTIONABLE = "questionable" 
    DOUBTFUL = "doubtful"
    OUT = "out"
    IR = "injured_reserve"


class PlayerRole(Enum):
    STARTER = "starter"
    BACKUP = "backup"
    DEPTH = "depth"
    PRACTICE_SQUAD = "practice_squad"


@dataclass
class Player:
    """Base player class with core attributes for simulation"""
    
    # Identity
    id: str
    name: str
    position: str
    team_id: int
    
    # Core Physical Attributes (0-100 scale)
    speed: int          # 40-yard dash, breakaway ability
    strength: int       # Power, ability to break/make tackles
    agility: int        # Change of direction, cutting ability
    stamina: int        # Endurance, late-game performance
    
    # Mental Attributes
    awareness: int      # Football IQ, reading plays
    technique: int      # Position-specific fundamentals
    
    # Game State
    fatigue: int = 100       # Current energy level (0-100)
    injury_status: InjuryStatus = InjuryStatus.HEALTHY
    role: PlayerRole = PlayerRole.STARTER
    snaps_played: int = 0    # Snaps played in current game
    
    # Additional attributes for extensibility
    additional_ratings: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate ratings are within bounds"""
        for attr in ['speed', 'strength', 'agility', 'stamina', 'awareness', 'technique']:
            value = getattr(self, attr)
            if not 0 <= value <= 100:
                raise ValueError(f"{attr} must be between 0-100, got {value}")
    
    @property 
    def overall_rating(self) -> int:
        """Calculate overall player rating based on core attributes"""
        # Base calculation - can be overridden by position-specific classes
        return int((self.speed + self.strength + self.agility + 
                   self.awareness + self.technique) / 5)
    
    @property
    def effective_rating(self) -> int:
        """Get overall rating adjusted for fatigue and injury"""
        base_rating = self.overall_rating
        
        # Fatigue penalty (10% reduction at 50% fatigue, 25% at 0% fatigue)
        fatigue_multiplier = 0.75 + (self.fatigue / 100) * 0.25
        
        # Injury penalty
        injury_multiplier = {
            InjuryStatus.HEALTHY: 1.0,
            InjuryStatus.DAY_TO_DAY: 0.95,
            InjuryStatus.QUESTIONABLE: 0.90,
            InjuryStatus.DOUBTFUL: 0.80,
            InjuryStatus.OUT: 0.0,
            InjuryStatus.IR: 0.0
        }[self.injury_status]
        
        return int(base_rating * fatigue_multiplier * injury_multiplier)
    
    def apply_fatigue(self, snap_fatigue: int = 2) -> None:
        """Apply fatigue from playing a snap"""
        # Higher stamina players lose less fatigue
        stamina_factor = (100 - self.stamina) / 100
        actual_fatigue = snap_fatigue * (1 + stamina_factor)
        
        self.fatigue = max(0, self.fatigue - actual_fatigue)
        self.snaps_played += 1
    
    def rest(self, rest_amount: int = 5) -> None:
        """Recover fatigue from resting/being on bench"""
        self.fatigue = min(100, self.fatigue + rest_amount)
    
    def get_attribute(self, attribute: str) -> int:
        """Get any attribute value, including position-specific ones"""
        if hasattr(self, attribute):
            return getattr(self, attribute)
        return self.additional_ratings.get(attribute, 50)  # Default to average
    
    def get_effective_attribute(self, attribute: str) -> int:
        """Get attribute adjusted for fatigue and injury"""
        base_value = self.get_attribute(attribute)
        
        # Apply same adjustments as overall rating
        fatigue_multiplier = 0.75 + (self.fatigue / 100) * 0.25
        
        injury_multiplier = {
            InjuryStatus.HEALTHY: 1.0,
            InjuryStatus.DAY_TO_DAY: 0.95,
            InjuryStatus.QUESTIONABLE: 0.90,
            InjuryStatus.DOUBTFUL: 0.80,
            InjuryStatus.OUT: 0.0,
            InjuryStatus.IR: 0.0
        }[self.injury_status]
        
        return int(base_value * fatigue_multiplier * injury_multiplier)
    
    def is_available(self) -> bool:
        """Check if player is available to play"""
        return self.injury_status not in [InjuryStatus.OUT, InjuryStatus.IR]
    
    def reset_game_state(self) -> None:
        """Reset game-specific state (fatigue, snaps) for new game"""
        self.fatigue = 100
        self.snaps_played = 0
    
    def __str__(self) -> str:
        return f"{self.name} ({self.position}) - OVR: {self.overall_rating}"
    
    def __repr__(self) -> str:
        return f"Player(name='{self.name}', position='{self.position}', overall={self.overall_rating})"