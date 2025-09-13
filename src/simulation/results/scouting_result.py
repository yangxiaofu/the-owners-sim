"""
Scouting Result

Specialized result class for scouting activities including prospect evaluations,
opponent analysis, and intelligence gathering that affects draft boards and game planning.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .base_result import SimulationResult, EventType


@dataclass
class ProspectEvaluation:
    """Evaluation of a college or pro prospect"""
    prospect_name: str
    position: str
    school_or_team: str
    
    # Physical attributes (1-100 scale)
    height_inches: int = 72
    weight_lbs: int = 200
    speed_rating: int = 50
    strength_rating: int = 50
    agility_rating: int = 50
    
    # Skill ratings (1-100 scale)
    overall_rating: int = 50
    potential_rating: int = 50
    technique_rating: int = 50
    football_iq: int = 50
    work_ethic: int = 50
    leadership: int = 50
    
    # Position-specific ratings
    position_specific_ratings: Dict[str, int] = field(default_factory=dict)
    
    # Character and background
    character_concerns: List[str] = field(default_factory=list)
    injury_history: List[str] = field(default_factory=list)
    background_notes: List[str] = field(default_factory=list)
    
    # Draft projection
    projected_draft_round: int = 7
    projected_pick_range: str = "Late"  # "Early", "Mid", "Late"
    nfl_readiness: str = "Developmental"  # "Immediate", "Year_2", "Developmental"
    
    # Scouting confidence
    evaluation_confidence: float = 0.5  # 0.0-1.0, how confident scouts are
    times_scouted: int = 1
    consensus_rating: bool = False  # True if multiple scouts agree
    
    def get_overall_grade(self) -> str:
        """Get letter grade for overall evaluation"""
        if self.overall_rating >= 90:
            return "A+"
        elif self.overall_rating >= 85:
            return "A"
        elif self.overall_rating >= 80:
            return "A-"
        elif self.overall_rating >= 75:
            return "B+"
        elif self.overall_rating >= 70:
            return "B"
        elif self.overall_rating >= 65:
            return "B-"
        elif self.overall_rating >= 60:
            return "C+"
        elif self.overall_rating >= 55:
            return "C"
        else:
            return "C-"
    
    def has_red_flags(self) -> bool:
        """Check if prospect has significant concerns"""
        return (len(self.character_concerns) > 0 or 
                len(self.injury_history) > 1 or
                self.work_ethic < 40)
    
    def is_high_confidence_evaluation(self) -> bool:
        """Check if this is a high-confidence evaluation"""
        return self.evaluation_confidence >= 0.8 and self.times_scouted >= 3


@dataclass
class OpponentIntelligence:
    """Intelligence gathered about an opponent team"""
    opponent_team_id: int
    intelligence_type: str  # "tendencies", "personnel", "injuries", "strategy"
    
    # Offensive intelligence
    offensive_tendencies: Dict[str, float] = field(default_factory=dict)  # situation -> tendency %
    key_offensive_players: List[Dict[str, Any]] = field(default_factory=list)
    offensive_strengths: List[str] = field(default_factory=list)
    offensive_weaknesses: List[str] = field(default_factory=list)
    
    # Defensive intelligence
    defensive_schemes: List[str] = field(default_factory=list)
    defensive_personnel_packages: Dict[str, float] = field(default_factory=dict)  # package -> usage %
    key_defensive_players: List[Dict[str, Any]] = field(default_factory=list)
    defensive_strengths: List[str] = field(default_factory=list)
    defensive_weaknesses: List[str] = field(default_factory=list)
    
    # Special teams intelligence
    special_teams_tendencies: Dict[str, Any] = field(default_factory=dict)
    kicking_game_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Coaching patterns
    coaching_tendencies: Dict[str, float] = field(default_factory=dict)
    situational_calls: Dict[str, List[str]] = field(default_factory=dict)
    timeout_usage_patterns: List[str] = field(default_factory=list)
    
    # Recent performance trends
    recent_form: str = "unknown"  # "improving", "declining", "stable"
    injury_report_intel: List[Dict[str, Any]] = field(default_factory=list)
    
    # Intelligence quality and reliability
    intelligence_quality: float = 0.5  # 0.0-1.0
    source_reliability: str = "medium"  # "low", "medium", "high"
    information_age_days: int = 0
    
    def get_exploitable_weaknesses(self) -> List[str]:
        """Get list of exploitable weaknesses"""
        all_weaknesses = self.offensive_weaknesses + self.defensive_weaknesses
        return [w for w in all_weaknesses if "exploitable" in w.lower()]
    
    def is_high_quality_intel(self) -> bool:
        """Check if this is high-quality intelligence"""
        return (self.intelligence_quality >= 0.8 and 
                self.source_reliability == "high" and
                self.information_age_days <= 7)


@dataclass
class ScoutingMetrics:
    """Overall metrics for the scouting operation"""
    scouting_type: str  # "college_prospects", "pro_prospects", "opponent_analysis"
    scouts_deployed: int = 1
    locations_covered: List[str] = field(default_factory=list)
    
    # Resource utilization
    budget_spent: float = 0.0
    travel_expenses: float = 0.0
    time_invested_hours: int = 8
    
    # Coverage and thoroughness
    games_attended: int = 0
    practices_observed: int = 0
    interviews_conducted: int = 0
    tape_reviewed_hours: int = 0
    
    # Quality metrics
    information_accuracy: float = 0.8  # Historical accuracy of this scouting effort
    coverage_completeness: float = 0.7  # How complete the scouting coverage was
    actionable_insights_generated: int = 0
    
    # External factors
    weather_impact: str = "none"
    access_restrictions: List[str] = field(default_factory=list)
    competition_present: bool = False  # Other teams scouting same targets
    
    def get_efficiency_score(self) -> float:
        """Calculate efficiency of scouting operation"""
        if self.time_invested_hours == 0:
            return 0.0
        
        insights_per_hour = self.actionable_insights_generated / self.time_invested_hours
        return min(insights_per_hour * self.information_accuracy * self.coverage_completeness, 1.0)
    
    def was_comprehensive_scouting(self) -> bool:
        """Check if this was comprehensive scouting"""
        return (self.coverage_completeness >= 0.8 and
                self.games_attended >= 2 and
                self.tape_reviewed_hours >= 4)


@dataclass
class ScoutingResult(SimulationResult):
    """
    Specialized result for scouting activities.
    
    Contains prospect evaluations, opponent intelligence, and scouting effectiveness
    metrics that affect draft boards, game planning, and personnel decisions.
    """
    
    # Basic scouting info
    scouting_type: str = "prospects"
    team_id: int = 0
    target_description: str = ""
    
    # Prospect scouting results
    prospect_evaluations: List[ProspectEvaluation] = field(default_factory=list)
    
    # Opponent intelligence gathering
    opponent_intelligence: List[OpponentIntelligence] = field(default_factory=list)
    
    # Overall scouting operation metrics
    scouting_metrics: ScoutingMetrics = field(default_factory=ScoutingMetrics)
    
    # Draft board impacts
    draft_board_updates: Dict[str, Any] = field(default_factory=dict)  # Changes to team's draft board
    prospect_rankings_changes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Game planning impacts
    game_plan_recommendations: List[str] = field(default_factory=list)
    strategic_advantages_identified: List[str] = field(default_factory=list)
    
    # Personnel insights
    position_needs_identified: List[str] = field(default_factory=list)
    comparable_player_analysis: Dict[str, str] = field(default_factory=dict)  # prospect -> comparison
    
    # Intelligence value
    competitive_advantages_gained: List[str] = field(default_factory=list)
    information_shelf_life_days: int = 30  # How long this intelligence remains valuable
    
    # Scouting department impacts
    scout_performance_ratings: Dict[str, float] = field(default_factory=dict)  # scout_name -> performance
    scouting_network_expansions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.SCOUTING
        
        # Initialize metrics if not provided
        if not hasattr(self, 'scouting_metrics') or self.scouting_metrics is None:
            self.scouting_metrics = ScoutingMetrics()
            self.scouting_metrics.scouting_type = self.scouting_type
    
    def get_high_value_prospects(self) -> List[ProspectEvaluation]:
        """Get prospects with high ratings and potential"""
        return [p for p in self.prospect_evaluations 
                if p.overall_rating >= 75 and p.potential_rating >= 75]
    
    def get_red_flag_prospects(self) -> List[ProspectEvaluation]:
        """Get prospects with significant concerns"""
        return [p for p in self.prospect_evaluations if p.has_red_flags()]
    
    def get_high_quality_intelligence(self) -> List[OpponentIntelligence]:
        """Get high-quality opponent intelligence"""
        return [intel for intel in self.opponent_intelligence if intel.is_high_quality_intel()]
    
    def get_actionable_insights_count(self) -> int:
        """Get total actionable insights generated"""
        return (len(self.game_plan_recommendations) + 
                len(self.strategic_advantages_identified) +
                len(self.competitive_advantages_gained))
    
    def was_successful_scouting(self) -> bool:
        """Determine if scouting mission was successful"""
        return (self.scouting_metrics.get_efficiency_score() >= 0.6 and
                self.get_actionable_insights_count() >= 3 and
                self.success)
    
    def requires_draft_board_update(self) -> bool:
        """Check if draft board needs updating"""
        return (bool(self.prospect_evaluations) and 
                self.scouting_type in ["college_prospects", "pro_prospects"] and
                self.success)
    
    def requires_game_plan_update(self) -> bool:
        """Check if game planning needs updating"""
        return (bool(self.opponent_intelligence) and
                self.scouting_type == "opponent_analysis" and
                self.success)
    
    def get_scouting_summary(self) -> str:
        """Get comprehensive scouting summary"""
        prospects_found = len(self.prospect_evaluations)
        high_value = len(self.get_high_value_prospects())
        intel_pieces = len(self.opponent_intelligence)
        insights = self.get_actionable_insights_count()
        
        return (f"Scouting ({self.scouting_type}): {prospects_found} prospects "
                f"({high_value} high-value), {intel_pieces} intel pieces, "
                f"{insights} actionable insights")
    
    def add_game_plan_recommendation(self, recommendation: str) -> None:
        """Add a game planning recommendation"""
        self.game_plan_recommendations.append(recommendation)
    
    def add_strategic_advantage(self, advantage: str) -> None:
        """Add an identified strategic advantage"""
        self.strategic_advantages_identified.append(advantage)
    
    def add_competitive_advantage(self, advantage: str) -> None:
        """Add a competitive advantage gained"""
        self.competitive_advantages_gained.append(advantage)