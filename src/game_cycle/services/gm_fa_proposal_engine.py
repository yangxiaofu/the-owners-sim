"""
GM FA Proposal Engine - Generates free agent signing proposals based on GM archetype.

Part of Milestone 10: GM-Driven Free Agency with Owner Oversight.

Design:
- Analyzes available FA pool for current wave
- Scores candidates using archetype-weighted formula
- Generates contract offers aligned with GM personality
- Returns top N proposals for owner review
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
import random

from src.game_cycle.models import FAGuidance, FAPhilosophy, GMProposal
from src.team_management.gm_archetype import GMArchetype
from utils.player_field_extractors import extract_overall_rating

if TYPE_CHECKING:
    from src.game_cycle.services.valuation_service import ValuationService


class GMFAProposalEngine:
    """
    Generates GM free agent proposals based on archetype + guidance.

    Core logic:
    - Analyze available FA pool for current wave
    - Score candidates using archetype-weighted formula
    - Generate contract offers aligned with GM personality
    - Return top N proposals for owner review
    """

    def __init__(
        self,
        gm_archetype: GMArchetype,
        fa_guidance: FAGuidance,
        valuation_service: Optional["ValuationService"] = None,
        team_id: Optional[int] = None
    ):
        """
        Initialize proposal engine.

        Args:
            gm_archetype: GM's personality traits
            fa_guidance: Owner's strategic guidance
            valuation_service: Optional ContractValuationEngine service for sophisticated valuations
            team_id: Team ID (required if valuation_service provided)
        """
        self.gm = gm_archetype
        self.guidance = fa_guidance
        self._valuation_service = valuation_service
        self._team_id = team_id

        # Debug logging for GM proposal engine initialization
        print(f"[DEBUG] GMFAProposalEngine initialized: priority_positions={fa_guidance.priority_positions}")

        # Validation: if valuation_service provided, team_id is required
        if valuation_service and team_id is None:
            raise ValueError("team_id required when valuation_service is provided")

    def generate_proposals(
        self,
        available_players: List[Dict[str, Any]],
        team_needs: Dict[str, int],
        cap_space: int,
        wave: int
    ) -> List[GMProposal]:
        """
        Generate 1-3 proposals for current wave turn.

        Args:
            available_players: FAs available in current wave
            team_needs: Position needs (position → depth level, 0 = critical)
            cap_space: Available cap space
            wave: Current wave number (1-4)

        Returns:
            List of GMProposal objects (max 3)
        """
        # 1. Filter candidates by cap fit + tier
        candidates = self._filter_candidates(available_players, cap_space, wave)

        if not candidates:
            return []

        # 2. Score each candidate
        scored = []
        for player in candidates:
            score = self._score_candidate(player, team_needs, cap_space)
            if score > 60:  # Minimum threshold
                scored.append((player, score))

        if not scored:
            return []

        # 3. Sort by score, take top 3
        scored.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored[:3]

        # 4. Generate proposals
        proposals = []
        for player, score in top_candidates:
            proposal = self._create_proposal(player, score, team_needs, cap_space)
            if proposal:
                proposals.append(proposal)

        return proposals

    def _filter_candidates(
        self,
        available_players: List[Dict[str, Any]],
        cap_space: int,
        wave: int
    ) -> List[Dict[str, Any]]:
        """
        Filter candidates by cap fit and tier appropriateness.

        Args:
            available_players: All available FAs
            cap_space: Available cap space
            wave: Current wave number

        Returns:
            Filtered list of candidates
        """
        filtered = []

        for player in available_players:
            # Estimate minimum AAV needed (rough guess based on rating)
            min_aav = extract_overall_rating(player, default=0) * 100_000  # $100k per OVR point

            # Skip if clearly can't afford
            if min_aav > cap_space:
                continue

            # Philosophy-based tier filtering
            tier = player.get("tier", "Unknown")

            if self.guidance.philosophy == FAPhilosophy.AGGRESSIVE:
                # Aggressive: Focus on Elite tier
                if tier not in ["Elite", "Quality"]:
                    continue
            elif self.guidance.philosophy == FAPhilosophy.CONSERVATIVE:
                # Conservative: Focus on Depth tier
                if tier not in ["Depth", "Quality"]:
                    continue
            # Balanced: No tier filtering

            filtered.append(player)

        return filtered

    def _score_candidate(
        self,
        player: Dict[str, Any],
        needs: Dict[str, int],
        cap_space: int
    ) -> float:
        """
        Score candidate using archetype-weighted formula.

        Returns:
            Score (0-100+, higher = better fit)
        """
        score = float(extract_overall_rating(player, default=0))  # Base value

        # Archetype modifiers
        age = player.get("age", 25)

        # Veteran preference
        if age >= 30:
            if self.gm.veteran_preference > 0.7:
                score += 10
            elif self.gm.veteran_preference < 0.3:
                score -= 10

        # Youth preference (inverse of veteran)
        if age < 26:
            if self.gm.veteran_preference < 0.3:
                score += 8
            elif self.gm.veteran_preference > 0.7:
                score -= 5

        # Star chasing
        tier = player.get("tier", "Unknown")
        if tier == "Elite":
            if self.gm.star_chasing > 0.7:
                score += 15
            if self.gm.cap_management > 0.7:
                score -= 10  # Conservative GMs avoid expensive stars

        # Risk tolerance for injury-prone players
        # (Future enhancement - would check injury history)

        # Priority position bonus
        position = player.get("position", "")
        if position in self.guidance.priority_positions:
            score += 15
            player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
            print(f"[DEBUG] Priority position bonus +15 for {player_name} ({position})")

        # Wishlist bonus - owner's specific targets
        if self.guidance.wishlist_names:
            first_name = player.get("first_name", "")
            last_name = player.get("last_name", "")
            player_full_name = f"{first_name} {last_name}".strip()

            # Check full name or last name match (case-insensitive)
            for wishlist_name in self.guidance.wishlist_names:
                wishlist_lower = wishlist_name.lower()
                if (player_full_name.lower() == wishlist_lower or
                        last_name.lower() == wishlist_lower):
                    score += 20  # Strong bonus for owner's wishlist targets
                    break

        # Need urgency
        position_need = needs.get(position, 5)  # 0 = critical, 5 = no need
        if position_need <= 1:  # Critical/starter need
            score += 15
        elif position_need == 2:  # Backup need
            score += 10
        elif position_need == 3:  # Depth need
            score += 5

        # Philosophy alignment
        if self.guidance.philosophy == FAPhilosophy.AGGRESSIVE:
            if tier == "Elite":
                score += 10
        elif self.guidance.philosophy == FAPhilosophy.CONSERVATIVE:
            if tier == "Depth":
                score += 10

        # Random variance (±5 points) to avoid same players every time
        score += random.uniform(-5, 5)

        return score

    def _create_proposal(
        self,
        player: Dict[str, Any],
        score: float,
        needs: Dict[str, int],
        cap_space: int
    ) -> Optional[GMProposal]:
        """
        Generate contract offer based on archetype.

        Returns:
            GMProposal with terms + reasoning, or None if can't create valid offer
        """
        # Get tier and age for logic below
        tier = player.get("tier", "Unknown")
        age = player.get("age", 25)

        # Check if we should use the valuation engine
        if self._valuation_service and self._team_id:
            # Use sophisticated ContractValuationEngine
            try:
                valuation_result = self._valuation_service.valuate_player(
                    player_data=player,
                    team_id=self._team_id,
                    gm_archetype=self.gm,
                )
                aav = valuation_result.offer.aav
                years = valuation_result.offer.years
                guaranteed = valuation_result.offer.guaranteed

                # Adjust for FA guidance philosophy
                if self.guidance.philosophy == FAPhilosophy.AGGRESSIVE:
                    aav = int(aav * 1.05)  # +5% for aggressive approach
                    guaranteed = int(guaranteed * 1.1)  # +10% guaranteed
                elif self.guidance.philosophy == FAPhilosophy.CONSERVATIVE:
                    aav = int(aav * 0.95)  # -5% for conservative approach
                    guaranteed = int(guaranteed * 0.9)  # -10% guaranteed

                # Apply guidance year caps
                years = min(years, self.guidance.max_contract_years)

                # Apply guidance guaranteed cap (as % of total value)
                total_value = aav * years
                max_guaranteed = int(total_value * self.guidance.max_guaranteed_percent)
                guaranteed = min(guaranteed, max_guaranteed)

            except Exception as e:
                # Fallback to legacy formula if valuation fails
                print(f"[WARNING GMFAProposalEngine] Valuation engine failed, using legacy formula: {e}")
                aav, years, guaranteed = self._legacy_contract_calculation(
                    player, score, cap_space
                )
        else:
            # Use legacy formula (backward compatibility)
            aav, years, guaranteed = self._legacy_contract_calculation(
                player, score, cap_space
            )

        # Cap check - can't exceed available space
        if aav > cap_space:
            return None  # Can't afford this player

        # Signing bonus (30% of guaranteed as upfront money)
        signing_bonus = int(guaranteed * 0.3)

        # Cap impact (Year 1 cap hit)
        cap_impact = aav + signing_bonus

        # Double-check cap space after bonus
        if cap_impact > cap_space:
            # Reduce signing bonus to fit cap
            signing_bonus = max(0, cap_space - aav)
            cap_impact = aav + signing_bonus

        remaining_cap = cap_space - cap_impact

        # Generate pitch
        pitch = self._generate_pitch(player, needs, score, tier)

        # Generate archetype rationale
        # Include valuation result if available
        valuation_description = None
        if self._valuation_service and self._team_id:
            try:
                valuation_result = self._valuation_service.valuate_player(
                    player_data=player,
                    team_id=self._team_id,
                    gm_archetype=self.gm,
                )
                valuation_description = valuation_result.gm_style_description
            except Exception:
                pass

        rationale = self._generate_archetype_rationale(
            player, aav, years, tier, valuation_description
        )

        # Determine need addressed
        position = player.get("position", "")
        position_need = needs.get(position, 5)
        if position_need == 0:
            need_text = f"{position} starter (CRITICAL NEED)"
        elif position_need == 1:
            need_text = f"{position} starter/backup (high need)"
        elif position_need == 2:
            need_text = f"{position} backup (moderate need)"
        elif position_need == 3:
            need_text = f"{position} depth (low need)"
        else:
            need_text = f"{position} depth (optional)"

        # Create proposal
        try:
            proposal = GMProposal(
                player_id=player.get("player_id", 0),
                player_name=player.get("full_name", player.get("name", "Unknown")),
                position=position,
                age=age,
                overall_rating=extract_overall_rating(player, default=0),
                tier=tier,
                aav=aav,
                years=years,
                guaranteed=guaranteed,
                signing_bonus=signing_bonus,
                pitch=pitch,
                archetype_rationale=rationale,
                need_addressed=need_text,
                cap_impact=cap_impact,
                remaining_cap_after=remaining_cap,
                score_breakdown={
                    "base": float(extract_overall_rating(player, default=0)),
                    "archetype_fit": score - float(extract_overall_rating(player, default=0)),
                    "total": score,
                }
            )
            return proposal
        except ValueError as e:
            # Validation failed, skip this proposal
            print(f"[WARNING GMFAProposalEngine] Failed to create proposal: {e}")
            return None

    def _generate_pitch(
        self,
        player: Dict[str, Any],
        needs: Dict[str, int],
        score: float,
        tier: str
    ) -> str:
        """Generate human-readable pitch text."""
        position = player.get("position", "")
        position_need = needs.get(position, 5)
        name = player.get("full_name", player.get("name", "Unknown"))
        age = player.get("age", 25)
        overall = extract_overall_rating(player, default=0)

        # Urgency based on score
        if score > 90:
            urgency = "Perfect fit"
        elif score > 80:
            urgency = "Strong fit"
        elif score > 70:
            urgency = "Solid option"
        else:
            urgency = "Decent depth piece"

        # Need description
        if position_need == 0:
            need_desc = "critical starter need"
        elif position_need == 1:
            need_desc = "important roster gap"
        elif position_need == 2:
            need_desc = "backup depth"
        else:
            need_desc = "roster depth"

        # Tier description
        if tier == "Elite":
            tier_desc = "elite-tier talent"
        elif tier == "Quality":
            tier_desc = "quality starter"
        elif tier == "Depth":
            tier_desc = "solid depth player"
        else:
            tier_desc = "available player"

        # Combine
        pitch = (
            f"{urgency} for our {need_desc}. {name} ({age} yo, {overall} OVR) "
            f"is a {tier_desc} who can contribute immediately to our roster."
        )

        return pitch

    def _generate_archetype_rationale(
        self,
        player: Dict[str, Any],
        aav: int,
        years: int,
        tier: str,
        valuation_description: Optional[str] = None
    ) -> str:
        """Explain how proposal fits GM's archetype."""
        reasons = []

        # If we have a valuation description from the engine, use it first
        if valuation_description:
            reasons.append(valuation_description)

        # Star chasing
        if self.gm.star_chasing > 0.7 and tier == "Elite":
            reasons.append("Aligns with my star-chasing philosophy")

        # Veteran preference
        age = player.get("age", 25)
        if self.gm.veteran_preference > 0.7 and age >= 30:
            reasons.append("Veteran experience is crucial for winning now")
        elif self.gm.veteran_preference < 0.3 and age < 26:
            reasons.append("Young talent fits our rebuilding timeline")

        # Cap management
        if self.gm.cap_management > 0.7:
            reasons.append(f"Contract structure ({years}yr) protects future cap flexibility")

        # Win-now mentality
        if self.gm.win_now_mentality > 0.7 and tier in ["Elite", "Quality"]:
            reasons.append("Immediate impact player for our championship window")

        # Risk tolerance
        if self.gm.risk_tolerance > 0.7:
            reasons.append("Worth the investment for high upside")
        elif self.gm.risk_tolerance < 0.3:
            reasons.append("Safe, proven production minimizes risk")

        # Default if no specific reasons
        if not reasons:
            reasons.append("Balanced approach to roster building")

        return ". ".join(reasons) + "."

    def _legacy_contract_calculation(
        self,
        player: Dict[str, Any],
        score: float,
        cap_space: int
    ) -> tuple[int, int, int]:
        """
        Legacy contract calculation formula (pre-valuation engine).

        Returns:
            Tuple of (aav, years, guaranteed)
        """
        # Estimate market value (rough formula)
        base_market_value = extract_overall_rating(player, default=0) * 100_000

        # Adjust market value by tier
        tier = player.get("tier", "Unknown")
        if tier == "Elite":
            market_value = int(base_market_value * 1.5)
        elif tier == "Quality":
            market_value = int(base_market_value * 1.2)
        elif tier == "Depth":
            market_value = int(base_market_value * 0.8)
        else:
            market_value = base_market_value

        # AAV calculation based on archetype
        if self.gm.cap_management > 0.7:
            # Conservative: 85-95% market
            aav_percent = 0.85 + (self.gm.risk_tolerance * 0.10)
        elif self.gm.cap_management < 0.3:
            # Aggressive: 95-110% market
            aav_percent = 0.95 + (self.gm.star_chasing * 0.15)
        else:
            # Balanced: 90-100% market
            aav_percent = 0.90 + (score / 1000)  # Score-based adjustment

        # Apply philosophy modifier
        if self.guidance.philosophy == FAPhilosophy.AGGRESSIVE:
            aav_percent += 0.05  # +5% for aggressive approach
        elif self.guidance.philosophy == FAPhilosophy.CONSERVATIVE:
            aav_percent -= 0.05  # -5% for conservative approach

        aav = int(market_value * aav_percent)

        # Contract years based on archetype + age + guidance
        age = player.get("age", 25)

        if self.gm.risk_tolerance > 0.7:
            base_years = 5
        elif age >= 30:
            base_years = 2  # Short deals for older players
        elif age < 25:
            base_years = 4  # Longer deals for young players
        else:
            base_years = 3

        years = min(base_years, self.guidance.max_contract_years)

        # Guaranteed money based on archetype + guidance
        if self.gm.risk_tolerance > 0.7:
            base_guaranteed = 0.7  # High risk = high guarantees
        elif self.gm.cap_management > 0.7:
            base_guaranteed = 0.35  # Conservative = low guarantees
        else:
            base_guaranteed = 0.5  # Balanced

        # Apply philosophy modifier
        if self.guidance.philosophy == FAPhilosophy.AGGRESSIVE:
            base_guaranteed += 0.1
        elif self.guidance.philosophy == FAPhilosophy.CONSERVATIVE:
            base_guaranteed -= 0.1

        guaranteed_percent = min(base_guaranteed, self.guidance.max_guaranteed_percent)
        guaranteed = int(aav * years * guaranteed_percent)

        return aav, years, guaranteed
