"""
Training Result

Specialized result class for training/practice events with player skill development,
injury risk, team chemistry changes, and fatigue impacts.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .base_result import SimulationResult, EventType


@dataclass
class PlayerSkillChange:
    """Individual player skill development from training"""
    player_name: str
    position: str
    
    # Skill improvements (positive values) or declines (negative values)
    speed_change: float = 0.0
    strength_change: float = 0.0
    agility_change: float = 0.0
    awareness_change: float = 0.0
    
    # Position-specific skill changes
    throwing_accuracy_change: float = 0.0  # QB
    throwing_power_change: float = 0.0     # QB
    catching_change: float = 0.0           # WR/TE/RB
    route_running_change: float = 0.0      # WR/TE
    blocking_change: float = 0.0           # OL/FB
    tackling_change: float = 0.0           # Defense
    coverage_change: float = 0.0           # DB/LB
    
    # Overall development
    overall_rating_change: float = 0.0
    potential_change: float = 0.0
    development_trait_improvement: bool = False
    
    # Training-specific metrics
    effort_level: float = 1.0  # 0.0-2.0, affects development rate
    practice_performance: str = "average"  # "poor", "average", "good", "excellent"
    
    def get_total_development_points(self) -> float:
        """Calculate total development points gained"""
        return (self.speed_change + self.strength_change + self.agility_change + 
                self.awareness_change + abs(self.overall_rating_change))
    
    def has_significant_development(self) -> bool:
        """Check if player had meaningful development"""
        return self.get_total_development_points() >= 1.0 or self.development_trait_improvement


@dataclass 
class TrainingInjury:
    """Training-related injury information"""
    player_name: str
    injury_type: str  # "strain", "sprain", "fatigue", "collision"
    severity: str     # "minor", "moderate", "major"
    body_part: str    # "hamstring", "knee", "shoulder", etc.
    weeks_out: int
    occurred_during: str  # "drill", "scrimmage", "conditioning"
    
    def is_serious_injury(self) -> bool:
        """Check if this is a serious injury requiring extended time"""
        return self.severity in ["moderate", "major"] and self.weeks_out >= 2


@dataclass
class TeamChemistryChanges:
    """Changes to team chemistry and cohesion from training"""
    overall_chemistry_change: float = 0.0  # -10.0 to +10.0
    
    # Unit-specific chemistry changes
    offensive_line_chemistry: float = 0.0
    receiving_corps_chemistry: float = 0.0
    defensive_secondary_chemistry: float = 0.0
    linebacker_corps_chemistry: float = 0.0
    special_teams_chemistry: float = 0.0
    
    # Leadership and culture impacts
    veteran_leadership_influence: float = 0.0
    rookie_integration_success: float = 0.0
    coaching_rapport_change: float = 0.0
    
    # Specific chemistry events
    chemistry_events: List[str] = field(default_factory=list)
    
    def add_chemistry_event(self, event: str) -> None:
        """Add a notable chemistry event"""
        self.chemistry_events.append(event)
    
    def get_net_chemistry_change(self) -> float:
        """Calculate net chemistry change across all units"""
        return (self.overall_chemistry_change + self.offensive_line_chemistry + 
                self.receiving_corps_chemistry + self.defensive_secondary_chemistry +
                self.linebacker_corps_chemistry + self.special_teams_chemistry) / 6


@dataclass
class TrainingMetrics:
    """Overall training session metrics and effectiveness"""
    training_type: str  # "practice", "walkthrough", "conditioning", "position_drills"
    intensity_level: str  # "light", "moderate", "high", "max"
    focus_areas: List[str] = field(default_factory=list)  # ["passing", "run_defense", etc.]
    
    # Participation and engagement
    attendance_rate: float = 1.0  # Percentage of players who attended
    average_effort_level: float = 1.0  # Average effort across all players
    coaching_effectiveness: float = 1.0  # How well coaching staff executed
    
    # Weather and conditions
    weather_impact: str = "none"  # "none", "minor", "moderate", "severe"
    facility_quality: str = "standard"  # "poor", "standard", "excellent"
    
    # Training outcomes
    successful_drills: int = 0
    total_drills: int = 0
    major_mistakes: int = 0
    breakthrough_moments: int = 0
    
    def get_drill_success_rate(self) -> float:
        """Calculate percentage of successful drills"""
        if self.total_drills == 0:
            return 0.0
        return (self.successful_drills / self.total_drills) * 100
    
    def was_highly_effective(self) -> bool:
        """Check if training was highly effective"""
        return (self.get_drill_success_rate() >= 80.0 and 
                self.average_effort_level >= 1.5 and
                self.breakthrough_moments > 0)


@dataclass
class TrainingResult(SimulationResult):
    """
    Specialized result for training/practice events.
    
    Contains player development data, injury risks, team chemistry changes,
    and training effectiveness metrics for season-long progression tracking.
    """
    
    # Basic training info
    training_type: str = "practice"
    team_id: int = 0
    
    # Player development results
    player_developments: List[PlayerSkillChange] = field(default_factory=list)
    
    # Injuries and health impacts
    training_injuries: List[TrainingInjury] = field(default_factory=list)
    
    # Team-level impacts
    team_chemistry_changes: TeamChemistryChanges = field(default_factory=TeamChemistryChanges)
    
    # Overall training metrics
    training_metrics: TrainingMetrics = field(default_factory=TrainingMetrics)
    
    # Fatigue and conditioning impacts
    team_fatigue_change: float = 0.0  # Negative = more fatigue, positive = recovery
    individual_fatigue_changes: Dict[str, float] = field(default_factory=dict)  # player_name -> fatigue change
    
    # Coaching and system impacts
    playbook_mastery_improvements: Dict[str, float] = field(default_factory=dict)  # system -> improvement
    coaching_rapport_changes: Dict[str, float] = field(default_factory=dict)  # coach_type -> change
    
    # Notable events and storylines
    practice_highlights: List[str] = field(default_factory=list)
    discipline_incidents: List[str] = field(default_factory=list)
    breakthrough_performances: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.TRAINING
        
        # Initialize nested objects if not provided
        if not hasattr(self, 'team_chemistry_changes') or self.team_chemistry_changes is None:
            self.team_chemistry_changes = TeamChemistryChanges()
        
        if not hasattr(self, 'training_metrics') or self.training_metrics is None:
            self.training_metrics = TrainingMetrics()
            self.training_metrics.training_type = self.training_type
    
    def get_total_player_developments(self) -> int:
        """Get count of players who developed significantly"""
        return sum(1 for dev in self.player_developments if dev.has_significant_development())
    
    def get_injury_count(self) -> int:
        """Get total number of training injuries"""
        return len(self.training_injuries)
    
    def get_serious_injury_count(self) -> int:
        """Get count of serious injuries requiring extended time"""
        return sum(1 for injury in self.training_injuries if injury.is_serious_injury())
    
    def had_successful_training(self) -> bool:
        """Determine if training was considered successful overall"""
        return (self.training_metrics.was_highly_effective() and 
                self.get_serious_injury_count() == 0 and
                self.team_chemistry_changes.get_net_chemistry_change() >= 0)
    
    def get_development_summary(self) -> str:
        """Get summary of player development"""
        total_dev = self.get_total_player_developments()
        significant_dev = sum(1 for dev in self.player_developments 
                            if dev.get_total_development_points() >= 2.0)
        return f"{total_dev} players developed ({significant_dev} significantly)"
    
    def requires_injury_processing(self) -> bool:
        """Check if training resulted in injuries needing processing"""
        return bool(self.training_injuries) and self.success
    
    def requires_chemistry_updates(self) -> bool:
        """Check if team chemistry needs updating"""
        return abs(self.team_chemistry_changes.get_net_chemistry_change()) >= 0.5
    
    def requires_skill_updates(self) -> bool:
        """Check if player skills need updating"""
        return bool(self.player_developments) and self.success
    
    def add_practice_highlight(self, description: str) -> None:
        """Add a notable practice highlight"""
        self.practice_highlights.append(description)
    
    def add_breakthrough_performance(self, player_name: str, description: str) -> None:
        """Add a breakthrough performance"""
        self.breakthrough_performances.append(f"{player_name}: {description}")
    
    def add_discipline_incident(self, description: str) -> None:
        """Add a discipline incident"""
        self.discipline_incidents.append(description)
    
    def get_training_summary(self) -> str:
        """Get comprehensive training summary"""
        effectiveness = "highly effective" if self.training_metrics.was_highly_effective() else "standard"
        return (f"Training ({self.training_type}): {effectiveness} - "
                f"{self.get_development_summary()} - "
                f"{self.get_injury_count()} injuries - "
                f"Chemistry: {self.team_chemistry_changes.get_net_chemistry_change():+.1f}")