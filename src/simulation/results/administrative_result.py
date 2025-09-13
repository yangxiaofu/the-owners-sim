"""
Administrative Result

Specialized result class for front office and administrative activities including
contract negotiations, trades, signings, and other business operations.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .base_result import SimulationResult, EventType


@dataclass
class ContractNegotiation:
    """Contract negotiation details"""
    player_name: str
    negotiation_type: str  # "extension", "new_contract", "renegotiation"
    current_status: str   # "initiated", "progressing", "completed", "stalled", "failed"
    
    contract_details: Dict[str, Any] = field(default_factory=dict)
    agent_demands: List[str] = field(default_factory=list)
    team_offers: List[Dict[str, Any]] = field(default_factory=list)
    
    negotiation_progress: float = 0.0  # 0.0-1.0
    sticking_points: List[str] = field(default_factory=list)
    breakthrough_moments: List[str] = field(default_factory=list)


@dataclass
class TradeDiscussion:
    """Trade discussion and negotiation details"""
    partner_team_id: int
    discussion_type: str  # "exploratory", "serious", "finalized"
    
    players_offered: List[str] = field(default_factory=list)
    players_requested: List[str] = field(default_factory=list)
    draft_picks_involved: List[str] = field(default_factory=list)
    
    negotiation_temperature: str = "lukewarm"  # "cold", "lukewarm", "warm", "hot"
    likelihood_of_completion: float = 0.2  # 0.0-1.0


@dataclass
class AdministrativeResult(SimulationResult):
    """
    Specialized result for administrative/front office activities.
    
    Contains contract negotiations, trade discussions, personnel moves,
    and other business operations that affect team composition and salary cap.
    """
    
    admin_type: str = "general"
    team_id: int = 0
    
    # Contract and personnel activities
    contract_negotiations: List[ContractNegotiation] = field(default_factory=list)
    trade_discussions: List[TradeDiscussion] = field(default_factory=list)
    
    # Roster moves
    players_signed: List[str] = field(default_factory=list)
    players_released: List[str] = field(default_factory=list)
    practice_squad_moves: List[str] = field(default_factory=list)
    
    # Financial impacts
    salary_cap_changes: float = 0.0
    contract_values_negotiated: float = 0.0
    cap_space_created: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.ADMINISTRATIVE