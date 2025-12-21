"""
FA Signing Proposal Generator - Converts GMFAProposalEngine output to persistent proposals.

Part of Tollgate 7: Free Agency Integration.

Takes ephemeral GMProposal objects from GMFAProposalEngine and converts them
to PersistentGMProposal objects for database storage and owner approval workflow.
"""

from datetime import datetime
from typing import Any, Dict, List

from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_signing_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus
from game_cycle.models.gm_proposal import GMProposal
from game_cycle.models.fa_guidance import FA_WAVE_PROPOSAL_LIMITS
from game_cycle.services.owner_influence_calculator import OwnerInfluenceCalculator


class FASigningProposalGenerator:
    """
    Converts GMFAProposalEngine output to persistent proposals.

    Takes ephemeral GMProposal objects and creates PersistentGMProposal
    objects ready for database persistence and owner approval.

    Wave batching limits:
    - Wave 1 (Elite): max 3 proposals
    - Wave 2 (Quality): max 5 proposals
    - Wave 3 (Depth): max 7 proposals
    - Wave 4 (Post-Draft): max 5 proposals

    Note: GMFAProposalEngine dynamically generates 1-N proposals per wave based on
    team needs, cap space, and GM archetype, respecting these wave limits as ceilings.
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        team_id: int,
        directives: OwnerDirectives,
    ):
        """
        Initialize the generator.

        Args:
            db_path: Path to database
            dynasty_id: Dynasty identifier
            season: Current season year
            team_id: User's team ID
            directives: Owner's strategic directives
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._team_id = team_id
        self._directives = directives

    def generate_proposals(
        self,
        gm_proposals: List[GMProposal],
        wave_number: int,
        cap_space: int,
    ) -> List[PersistentGMProposal]:
        """
        Convert GMProposal objects to PersistentGMProposal objects.

        Args:
            gm_proposals: List of ephemeral GMProposal from GMFAProposalEngine
            wave_number: Current FA wave (1-4)
            cap_space: Available cap space

        Returns:
            List of PersistentGMProposal objects ready for database persistence
        """
        if not gm_proposals:
            return []

        # Apply wave limit
        max_proposals = FA_WAVE_PROPOSAL_LIMITS.get(wave_number, 3)
        limited_proposals = gm_proposals[:max_proposals]

        persistent_proposals = []
        for gm_proposal in limited_proposals:
            try:
                persistent = self._convert_to_persistent(
                    gm_proposal, wave_number, cap_space
                )
                persistent_proposals.append(persistent)
            except ValueError as e:
                # Log but continue with other proposals
                print(f"[WARNING FASigningGenerator] Failed to convert proposal: {e}")
                continue

        return persistent_proposals

    def _convert_to_persistent(
        self,
        gm_proposal: GMProposal,
        wave_number: int,
        cap_space: int,
    ) -> PersistentGMProposal:
        """
        Convert a single GMProposal to PersistentGMProposal.

        Args:
            gm_proposal: Ephemeral proposal from GMFAProposalEngine
            wave_number: Current wave for priority calculation
            cap_space: Cap space before signing

        Returns:
            PersistentGMProposal ready for database storage
        """
        # Build contract details
        contract = {
            "years": gm_proposal.years,
            "total_value": gm_proposal.aav * gm_proposal.years,
            "guaranteed_money": gm_proposal.guaranteed,
            "aav": gm_proposal.aav,
            "contract_years": gm_proposal.years,
        }

        # Apply owner contract constraints
        calculator = OwnerInfluenceCalculator()
        contract = calculator.apply_contract_constraints(contract, self._directives)

        # Recalculate total and AAV after constraint application
        final_years = contract["contract_years"]
        contract["total"] = contract["total_value"]
        contract["guaranteed"] = contract["guaranteed_money"]
        contract["years"] = final_years
        contract["aav"] = contract["total"] // final_years if final_years > 0 else contract["total"]

        # Calculate cap space after signing (using constrained AAV)
        cap_space_after = cap_space - contract["aav"]

        # Create signing details using helper
        details = create_signing_details(
            player_name=gm_proposal.player_name,
            position=gm_proposal.position,
            age=gm_proposal.age,
            overall_rating=gm_proposal.overall_rating,
            contract=contract,
            cap_space_before=cap_space,
            cap_space_after=cap_space_after,
            competing_offers=0,  # TODO: track from FAWaveService when available
        )

        # Add additional context from GMProposal
        details["tier"] = gm_proposal.tier
        details["need_addressed"] = gm_proposal.need_addressed
        details["signing_bonus"] = gm_proposal.signing_bonus
        details["cap_impact"] = gm_proposal.cap_impact

        # Calculate confidence from score breakdown
        confidence = self._calculate_confidence(gm_proposal)

        # Use archetype rationale + pitch for comprehensive reasoning
        reasoning = gm_proposal.pitch
        if gm_proposal.archetype_rationale:
            reasoning += f"\n\nGM Analysis: {gm_proposal.archetype_rationale}"

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_FREE_AGENCY",
            proposal_type=ProposalType.SIGNING,
            subject_player_id=str(gm_proposal.player_id),
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=self._wave_to_priority(wave_number),
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )

    def _calculate_confidence(self, gm_proposal: GMProposal) -> float:
        """
        Calculate confidence score from GMProposal score breakdown.

        Higher scoring proposals get higher confidence.

        Args:
            gm_proposal: The proposal to evaluate

        Returns:
            Confidence value between 0.5 and 0.95
        """
        base = 0.6

        # Get total score from breakdown
        score = 70  # Default
        if gm_proposal.score_breakdown:
            score = gm_proposal.score_breakdown.get("total", 70)

        # Higher score = higher confidence
        # Score of 60 = 0.60 confidence
        # Score of 80 = 0.80 confidence
        # Score of 100 = 1.00 confidence (capped at 0.95)
        bonus = (score - 60) * 0.01

        return min(0.95, max(0.5, base + bonus))

    def _wave_to_priority(self, wave: int) -> int:
        """
        Convert wave number to priority.

        Earlier waves get higher priority (lower number).

        Args:
            wave: Wave number (1-4)

        Returns:
            Priority value (1 = highest)
        """
        return wave
