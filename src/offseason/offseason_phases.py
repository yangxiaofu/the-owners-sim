"""
Offseason Phase Enumeration

Defines the sub-phases within the NFL offseason period,
from the Super Bowl through training camp.
"""

from enum import Enum


class OffseasonPhase(Enum):
    """
    NFL offseason phases based on calendar dates.

    The offseason follows a structured timeline with distinct phases,
    each with specific activities and deadlines.
    """

    POST_SUPER_BOWL = "post_super_bowl"
    """
    Period immediately after Super Bowl (Feb 9 - Feb 28).

    - No major transactions allowed
    - Teams evaluate rosters
    - Coaching changes and staff hires
    """

    FRANCHISE_TAG_PERIOD = "franchise_tag_period"
    """
    Franchise tag window (March 1 - March 5, 4PM ET).

    - Teams can apply franchise or transition tags
    - One tag per team (with rare exceptions)
    - Tagged players receive one-year contract at position average
    """

    PRE_FREE_AGENCY = "pre_free_agency"
    """
    Period between tag deadline and legal tampering (March 6 - March 10).

    - Final roster evaluations
    - Contract extension negotiations
    - Cap management preparations
    """

    FREE_AGENCY_LEGAL_TAMPERING = "free_agency_legal_tampering"
    """
    Legal tampering period (March 11, 12PM ET - March 13, 4PM ET).

    - Teams can negotiate with UFAs from other teams
    - No contracts can be signed yet
    - Agreements announced but unofficial
    """

    FREE_AGENCY_OPEN = "free_agency_open"
    """
    Free agency signing period (March 13, 4PM ET - April 23).

    - UFA signings official
    - RFA tender decisions
    - Exclusive rights free agents
    - Continues through draft
    """

    DRAFT = "draft"
    """
    NFL Draft (April 24-27, typically Thursday-Saturday).

    - 7 rounds, 32 picks per round (224 total)
    - Draft order based on previous season standings (reverse)
    - Compensatory picks awarded
    """

    POST_DRAFT = "post_draft"
    """
    Post-draft period (April 28 - August 25).

    - UDFA signings
    - Veteran free agency continues
    - OTAs and minicamp
    - Roster expansion to 90
    """

    ROSTER_CUTS = "roster_cuts"
    """
    Final roster cuts (August 26-29).

    - Reduce from 90 to 53-man roster
    - Practice squad formation (16 players)
    - Waiver wire activity
    """

    COMPLETE = "complete"
    """
    Offseason complete, ready for regular season.

    - 53-man rosters finalized
    - Practice squads set
    - Regular season begins (early September)
    """

    def __str__(self) -> str:
        """Return human-readable phase name."""
        return self.value.replace('_', ' ').title()

    @classmethod
    def get_display_name(cls, phase: 'OffseasonPhase') -> str:
        """
        Get user-friendly display name for phase.

        Args:
            phase: OffseasonPhase to get name for

        Returns:
            Human-readable phase name

        Example:
            >>> OffseasonPhase.get_display_name(OffseasonPhase.FRANCHISE_TAG_PERIOD)
            'Franchise Tag Period'
        """
        return str(phase)
