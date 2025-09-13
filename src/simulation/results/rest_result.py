"""
Rest Result

Specialized result class for rest days and recovery activities including
injury healing, fatigue recovery, mental health, and team preparation.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .base_result import SimulationResult, EventType


@dataclass
class InjuryRecovery:
    """Player injury recovery progress"""
    player_name: str
    injury_type: str
    recovery_progress: float = 0.0  # 0.0-1.0, how much healing occurred
    expected_return_weeks: int = 0
    setbacks: List[str] = field(default_factory=list)
    treatment_effectiveness: float = 1.0


@dataclass
class FatigueRecovery:
    """Team and individual fatigue recovery"""
    team_fatigue_reduction: float = 0.0
    individual_recoveries: Dict[str, float] = field(default_factory=dict)
    complete_recovery_count: int = 0


@dataclass
class RestResult(SimulationResult):
    """
    Specialized result for rest days and recovery activities.
    
    Contains injury recovery progress, fatigue reduction, mental health impacts,
    and team preparation effects from rest and recovery time.
    """
    
    rest_type: str = "recovery"
    team_id: int = 0
    
    # Recovery outcomes
    injury_recoveries: List[InjuryRecovery] = field(default_factory=list)
    fatigue_recovery: FatigueRecovery = field(default_factory=FatigueRecovery)
    
    # Mental and morale impacts
    team_morale_change: float = 0.0
    stress_reduction: float = 0.0
    mental_freshness_gain: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.REST_DAY