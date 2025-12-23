"""
Stage-specific data models for Game Cycle UI.

Consolidates data transfer between stage controllers and views.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set


@dataclass
class ResigningStageData:
    """
    Consolidated data for ResigningView updates.

    Replaces multiple setter calls with a single update method.

    Attributes:
        recommendations: All expiring player recommendations with GM suggestions
        restructure_proposals: GM-generated restructure proposals for cap relief
        cap_data: Current cap situation (available_space, total_spending, etc.)
        roster_players: Full roster for health widget (optional)
        expiring_ids: Set of expiring player IDs (optional)
        is_reevaluation: Whether this is a GM re-evaluation (triggers animation)
    """
    recommendations: List[Dict]
    restructure_proposals: List[Dict]
    cap_data: Dict
    roster_players: Optional[List[Dict]] = None
    expiring_ids: Optional[Set[int]] = None
    is_reevaluation: bool = False
