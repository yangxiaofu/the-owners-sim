"""
Position-Specific Graders

Each position group has a dedicated grader that calculates component grades
based on position-specific criteria.

Position Groups:
- QB: Quarterbacks
- RB: Running backs (RB, FB)
- WR: Wide receivers and tight ends (WR, TE)
- OL: Offensive line (LT, LG, C, RG, RT)
- DL: Defensive line (LE, DT, RE, EDGE)
- LB: Linebackers (LOLB, MLB, ROLB)
- DB: Defensive backs (CB, FS, SS)
"""

from .base_grader import BasePositionGrader
from .qb_grader import QBGrader
from .rb_grader import RBGrader
from .wr_grader import WRGrader
from .ol_grader import OLGrader
from .dl_grader import DLGrader
from .lb_grader import LBGrader
from .db_grader import DBGrader
from .st_grader import STGrader

__all__ = [
    "BasePositionGrader",
    "QBGrader",
    "RBGrader",
    "WRGrader",
    "OLGrader",
    "DLGrader",
    "LBGrader",
    "DBGrader",
    "STGrader",
]

# Mapping of position groups to grader classes
POSITION_GRADERS = {
    "QB": QBGrader,
    "RB": RBGrader,
    "WR": WRGrader,
    "TE": WRGrader,  # TE uses WR grader with blocking emphasis
    "OL": OLGrader,
    "DL": DLGrader,
    "LB": LBGrader,
    "DB": DBGrader,
    "ST": STGrader,
    "K": lambda: STGrader(is_punter=False),
    "P": lambda: STGrader(is_punter=True),
}


def get_grader_for_position(position: str) -> BasePositionGrader:
    """Get the appropriate grader for a position."""
    from analytics.grading_constants import get_position_group

    group = get_position_group(position)
    grader_class = POSITION_GRADERS.get(group, BasePositionGrader)
    return grader_class()


def create_all_graders() -> dict:
    """Create instances of all position graders."""
    return {
        "QB": QBGrader(),
        "RB": RBGrader(),
        "WR": WRGrader(),
        "OL": OLGrader(),
        "DL": DLGrader(),
        "LB": LBGrader(),
        "DB": DBGrader(),
        "K": STGrader(is_punter=False),
        "P": STGrader(is_punter=True),
    }
