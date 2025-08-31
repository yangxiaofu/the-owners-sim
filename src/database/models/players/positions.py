from dataclasses import dataclass
from typing import Dict
from .player import Player, PlayerRole, InjuryStatus


@dataclass
class RunningBack(Player):
    """Running back with specialized attributes for rushing plays"""
    
    # RB-specific attributes (providing defaults for dataclass inheritance)
    vision: int = 50         # Ability to see holes and cutback lanes
    power: int = 50          # Breaking tackles, running through contact
    elusiveness: int = 50    # Making defenders miss, juking
    catching: int = 50       # Receiving out of backfield
    pass_blocking: int = 50  # Pass protection ability
    
    def __post_init__(self):
        """Initialize RB and validate all ratings"""
        super().__post_init__()
        
        # Validate RB-specific ratings
        for attr in ['vision', 'power', 'elusiveness', 'catching', 'pass_blocking']:
            value = getattr(self, attr)
            if not 0 <= value <= 100:
                raise ValueError(f"{attr} must be between 0-100, got {value}")
    
    @property
    def overall_rating(self) -> int:
        """Calculate RB overall rating with position-specific weighting"""
        # RB rating emphasizes speed, agility, vision, power
        return int((self.speed * 0.25 + self.agility * 0.20 + 
                   self.vision * 0.20 + self.power * 0.15 + 
                   self.elusiveness * 0.10 + self.strength * 0.10))
    
    @property
    def rushing_rating(self) -> int:
        """Specialized rating for rushing plays"""
        return int((self.speed * 0.3 + self.vision * 0.25 + 
                   self.power * 0.20 + self.agility * 0.15 + 
                   self.elusiveness * 0.10))
    
    def get_gap_preference(self) -> str:
        """Determine RB's preferred running style based on attributes"""
        if self.power > 85 and self.speed < 75:
            return "power"  # Between the tackles power runner
        elif self.speed > 85 and self.agility > 80:
            return "outside"  # Outside zone, stretch plays
        elif self.vision > 85:
            return "zone"  # Zone running, patient runner
        else:
            return "balanced"  # No strong preference


@dataclass 
class OffensiveLineman(Player):
    """Offensive lineman with specialized blocking attributes"""
    
    # OL-specific attributes (providing defaults for dataclass inheritance)
    pass_blocking: int = 50    # Pass protection technique and strength
    run_blocking: int = 50     # Run blocking, drive blocking
    mobility: int = 50         # Ability to get to second level, pull
    anchor: int = 50          # Ability to hold ground against bull rush
    
    def __post_init__(self):
        """Initialize OL and validate all ratings"""
        super().__post_init__()
        
        # Validate OL-specific ratings
        for attr in ['pass_blocking', 'run_blocking', 'mobility', 'anchor']:
            value = getattr(self, attr)
            if not 0 <= value <= 100:
                raise ValueError(f"{attr} must be between 0-100, got {value}")
    
    @property
    def overall_rating(self) -> int:
        """Calculate OL overall rating with position-specific weighting"""
        return int((self.run_blocking * 0.25 + self.pass_blocking * 0.25 + 
                   self.strength * 0.20 + self.technique * 0.15 + 
                   self.anchor * 0.10 + self.mobility * 0.05))
    
    @property
    def zone_blocking_rating(self) -> int:
        """Rating for zone blocking schemes"""
        return int((self.mobility * 0.3 + self.agility * 0.25 + 
                   self.technique * 0.25 + self.run_blocking * 0.20))
    
    @property  
    def power_blocking_rating(self) -> int:
        """Rating for power/gap blocking schemes"""
        return int((self.strength * 0.3 + self.run_blocking * 0.25 + 
                   self.anchor * 0.25 + self.technique * 0.20))


@dataclass
class DefensiveLineman(Player):
    """Defensive lineman with specialized pass rush and run defense attributes"""
    
    # DL-specific attributes (providing defaults for dataclass inheritance)
    pass_rushing: int = 50     # Pass rush moves, speed, technique
    run_defense: int = 50      # Run stopping, gap control
    power_moves: int = 50      # Bull rush, strength-based moves
    finesse_moves: int = 50    # Speed rush, spin moves, etc.
    gap_discipline: int = 50   # Staying in assigned gap vs run
    
    def __post_init__(self):
        """Initialize DL and validate all ratings"""
        super().__post_init__()
        
        # Validate DL-specific ratings
        for attr in ['pass_rushing', 'run_defense', 'power_moves', 'finesse_moves', 'gap_discipline']:
            value = getattr(self, attr)
            if not 0 <= value <= 100:
                raise ValueError(f"{attr} must be between 0-100, got {value}")
    
    @property
    def overall_rating(self) -> int:
        """Calculate DL overall rating with position-specific weighting"""
        return int((self.run_defense * 0.25 + self.pass_rushing * 0.25 + 
                   self.strength * 0.20 + self.technique * 0.15 + 
                   self.power_moves * 0.10 + self.finesse_moves * 0.05))
    
    @property
    def run_stopping_rating(self) -> int:
        """Specialized rating for run defense"""
        return int((self.run_defense * 0.35 + self.strength * 0.25 + 
                   self.gap_discipline * 0.20 + self.technique * 0.20))
    
    def get_rush_style(self) -> str:
        """Determine DL's preferred pass rush style"""
        if self.power_moves > 85 and self.strength > 80:
            return "power"
        elif self.finesse_moves > 85 and self.speed > 75:
            return "finesse"
        else:
            return "balanced"


@dataclass
class Linebacker(Player):
    """Linebacker with attributes for run defense and coverage"""
    
    # LB-specific attributes (providing defaults for dataclass inheritance)
    run_defense: int = 50      # Tackling, run fits, gap control
    coverage: int = 50         # Pass coverage, zone/man ability
    blitzing: int = 50        # Pass rushing from LB position
    pursuit: int = 50         # Chasing down plays, sideline to sideline
    instincts: int = 50       # Reading plays, jumping routes
    
    def __post_init__(self):
        """Initialize LB and validate all ratings"""
        super().__post_init__()
        
        # Validate LB-specific ratings
        for attr in ['run_defense', 'coverage', 'blitzing', 'pursuit', 'instincts']:
            value = getattr(self, attr)
            if not 0 <= value <= 100:
                raise ValueError(f"{attr} must be between 0-100, got {value}")
    
    @property
    def overall_rating(self) -> int:
        """Calculate LB overall rating with position-specific weighting"""
        return int((self.run_defense * 0.25 + self.speed * 0.20 + 
                   self.coverage * 0.15 + self.instincts * 0.15 + 
                   self.awareness * 0.15 + self.pursuit * 0.10))
    
    @property
    def run_stopping_rating(self) -> int:
        """Specialized rating for run defense"""
        return int((self.run_defense * 0.35 + self.pursuit * 0.25 + 
                   self.instincts * 0.20 + self.strength * 0.20))
    
    @property
    def pass_coverage_rating(self) -> int:
        """Specialized rating for pass coverage"""
        return int((self.coverage * 0.35 + self.speed * 0.25 + 
                   self.agility * 0.20 + self.instincts * 0.20))
    
    def get_lb_type(self) -> str:
        """Determine LB's primary role based on attributes"""
        if self.run_defense > 85 and self.strength > 80:
            return "run_stopper"  # 3-4 ILB, run-first LB
        elif self.coverage > 85 and self.speed > 75:
            return "coverage"  # Nickel LB, cover guys
        elif self.speed > 85 and self.pursuit > 85:
            return "sideline"  # OLB, pursuit specialist
        else:
            return "balanced"  # Mike LB, do-it-all


# Factory functions for creating players
def create_running_back(name: str, team_id: int, position: str = "RB", 
                       base_ratings: Dict[str, int] = None, role: PlayerRole = PlayerRole.STARTER) -> RunningBack:
    """Create a RunningBack with realistic attribute distribution"""
    if base_ratings is None:
        base_ratings = {
            'speed': 75, 'strength': 70, 'agility': 75, 'stamina': 80, 
            'awareness': 65, 'technique': 70, 'vision': 75, 'power': 70, 
            'elusiveness': 75, 'catching': 60, 'pass_blocking': 50
        }
    
    return RunningBack(
        id=f"{team_id}_{position}_{name}",
        name=name,
        position=position,
        team_id=team_id,
        role=role,
        **base_ratings
    )


def create_offensive_lineman(name: str, team_id: int, position: str, 
                           base_ratings: Dict[str, int] = None, role: PlayerRole = PlayerRole.STARTER) -> OffensiveLineman:
    """Create an OffensiveLineman with realistic attribute distribution"""
    if base_ratings is None:
        base_ratings = {
            'speed': 45, 'strength': 85, 'agility': 55, 'stamina': 85,
            'awareness': 75, 'technique': 75, 'pass_blocking': 75, 
            'run_blocking': 75, 'mobility': 60, 'anchor': 80
        }
    
    return OffensiveLineman(
        id=f"{team_id}_{position}_{name}",
        name=name,
        position=position,
        team_id=team_id,
        role=role,
        **base_ratings
    )


def create_defensive_lineman(name: str, team_id: int, position: str,
                           base_ratings: Dict[str, int] = None, role: PlayerRole = PlayerRole.STARTER) -> DefensiveLineman:
    """Create a DefensiveLineman with realistic attribute distribution"""
    if base_ratings is None:
        base_ratings = {
            'speed': 60, 'strength': 85, 'agility': 60, 'stamina': 80,
            'awareness': 70, 'technique': 75, 'pass_rushing': 75,
            'run_defense': 80, 'power_moves': 75, 'finesse_moves': 65, 'gap_discipline': 80
        }
    
    return DefensiveLineman(
        id=f"{team_id}_{position}_{name}",
        name=name,
        position=position,
        team_id=team_id,
        role=role,
        **base_ratings
    )


def create_linebacker(name: str, team_id: int, position: str,
                     base_ratings: Dict[str, int] = None, role: PlayerRole = PlayerRole.STARTER) -> Linebacker:
    """Create a Linebacker with realistic attribute distribution"""
    if base_ratings is None:
        base_ratings = {
            'speed': 70, 'strength': 75, 'agility': 75, 'stamina': 85,
            'awareness': 80, 'technique': 75, 'run_defense': 80,
            'coverage': 65, 'blitzing': 70, 'pursuit': 80, 'instincts': 75
        }
    
    return Linebacker(
        id=f"{team_id}_{position}_{name}",
        name=name,
        position=position,
        team_id=team_id,
        role=role,
        **base_ratings
    )