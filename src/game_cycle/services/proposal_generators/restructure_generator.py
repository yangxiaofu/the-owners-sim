"""
Restructure Proposal Generator - GM analysis for contract restructure recommendations.

Part of Tollgate system: Contract restructure proposals.

Analyzes team cap situation and GM archetype to generate restructure proposals
that convert base salary to signing bonus for cap relief.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.player_field_extractors import extract_overall_rating
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_restructure_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus
from game_cycle.services.cap_helper import CapHelper
from salary_cap.cap_calculator import CapCalculator
from salary_cap.cap_database_api import CapDatabaseAPI
from team_management.gm_archetype import GMArchetype


class RestructureProposalGenerator:
    """
    Generates contract restructure proposals based on cap pressure and GM archetype.

    Identifies contracts that can be restructured to create immediate cap savings
    by converting base salary to signing bonus. Prioritizes based on:
    - Cap emergency (over cap)
    - Protected players
    - Star players (90+ OVR)
    - High-value players (80-89 OVR)
    - Proactive optimization

    GM Archetype Influence:
    - cap_management: Higher = more proactive restructuring
    - risk_tolerance: Higher = convert more base salary
    - win_now_mentality: Higher = prioritize immediate savings
    - loyalty: Higher = restructure to keep valued players
    - star_chasing: Higher = prioritize 90+ OVR players

    Priority tiers (lower number = higher priority):
    - Tier 1: Emergency (over cap)
    - Tier 2: Protected players
    - Tier 3: Star players (90+ OVR)
    - Tier 4: High-value players (80-89 OVR)
    - Tier 5: Proactive optimization
    """

    # Cap pressure thresholds
    CAP_EMERGENCY_THRESHOLD = 0  # At or over cap
    CAP_TIGHT_THRESHOLD = 10_000_000  # Less than $10M
    CAP_COMFORTABLE_THRESHOLD = 20_000_000  # More than $20M

    # Priority tiers
    TIER_EMERGENCY = 1  # Over cap - MUST restructure
    TIER_PROTECTED = 2  # Protected player
    TIER_STAR = 3  # 90+ OVR
    TIER_HIGH_VALUE = 4  # 80-89 OVR
    TIER_PROACTIVE = 5  # Optimization

    # Restructure constraints
    MIN_BASE_SALARY = 1_000_000  # Minimum base salary to consider restructuring
    MIN_YEARS_REMAINING = 2  # Need at least 2 years to prorate
    MIN_CAP_SAVINGS = 500_000  # Minimum savings to make it worthwhile
    MAX_PROPOSALS = 5  # Maximum proposals to generate

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        team_id: int,
        directives: OwnerDirectives,
        gm_archetype: GMArchetype,
    ):
        """
        Initialize the generator.

        Args:
            db_path: Path to database
            dynasty_id: Dynasty identifier
            season: Current season year
            team_id: User's team ID
            directives: Owner's strategic directives
            gm_archetype: GM personality and decision-making traits
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._team_id = team_id
        self._directives = directives
        self._gm_archetype = gm_archetype
        self._logger = logging.getLogger(__name__)

        # Initialize cap APIs (offseason cap calculations are for NEXT season)
        self._cap_helper = CapHelper(db_path, dynasty_id, season + 1)
        self._cap_calculator = CapCalculator(db_path)
        self._cap_db_api = CapDatabaseAPI(db_path, dynasty_id=dynasty_id)

    def generate_proposals(self) -> List[PersistentGMProposal]:
        """
        Generate restructure proposals for eligible contracts.

        Returns:
            List of PersistentGMProposal objects, sorted by priority (highest first)
        """
        # Get cap situation
        cap_summary = self._cap_helper.get_cap_summary(self._team_id)
        cap_space = cap_summary.get("available_space", 0)

        # Check if GM should propose restructures
        if not self._should_generate_proposals(cap_space):
            self._logger.debug(
                f"GM archetype (cap_management={self._gm_archetype.cap_management}) "
                f"does not propose restructures with ${cap_space:,} cap space"
            )
            return []

        # Get restructurable contracts
        candidates = self._get_restructurable_contracts()

        if not candidates:
            self._logger.debug("No restructurable contracts found")
            return []

        # Score and prioritize candidates
        proposals = []
        for candidate in candidates:
            score_data = self._score_candidate(candidate, cap_space)
            tier = self._determine_tier(candidate, cap_space)

            # Skip low-value proactive restructures unless GM is very cap-conscious
            if tier == self.TIER_PROACTIVE and self._gm_archetype.cap_management < 0.7:
                continue

            # Calculate restructure impact
            impact = self._calculate_restructure_impact(candidate)

            # Skip if savings too small
            if impact["cap_savings_current_year"] < self.MIN_CAP_SAVINGS:
                continue

            # Create proposal
            proposal = self._create_proposal(candidate, score_data, impact, cap_space, tier)
            proposals.append(proposal)

        # Sort by tier (ascending), then by cap savings (descending)
        proposals.sort(
            key=lambda p: (
                p.priority,
                -p.details.get("cap_savings", 0)
            )
        )

        # Limit to MAX_PROPOSALS
        return proposals[:self.MAX_PROPOSALS]

    def _should_generate_proposals(self, cap_space: int) -> bool:
        """
        Determine if GM should propose restructures based on archetype and cap situation.

        Args:
            cap_space: Available cap space (negative if over cap)

        Returns:
            True if GM should propose restructures
        """
        # Always propose if over cap (emergency)
        if cap_space <= self.CAP_EMERGENCY_THRESHOLD:
            return True

        # Tight cap + high cap_management GM
        if cap_space < self.CAP_TIGHT_THRESHOLD:
            if self._gm_archetype.cap_management >= 0.5:
                return True

        # Comfortable cap + very high cap_management GM (proactive)
        if cap_space < self.CAP_COMFORTABLE_THRESHOLD:
            if self._gm_archetype.cap_management >= 0.7:
                return True

        # Win-now mentality with cap pressure
        if (
            self._gm_archetype.win_now_mentality >= 0.7
            and cap_space < self.CAP_COMFORTABLE_THRESHOLD
        ):
            return True

        return False

    def _get_restructurable_contracts(self) -> List[Dict[str, Any]]:
        """
        Get contracts eligible for restructure.

        Criteria:
        - Active contracts for user's team
        - 2+ years remaining
        - Base salary >= $1M
        - Not a rookie contract (has contract_id in player_contracts)

        Returns:
            List of contract dicts with player info
        """
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get contracts with 2+ years remaining and significant base salary
            # Join with players to get name, position, attributes (contains overall/age)
            query = """
                SELECT
                    pc.contract_id,
                    pc.player_id,
                    pc.team_id,
                    pc.contract_years,
                    pc.total_value,
                    pc.signing_bonus,
                    pc.start_year,
                    p.first_name,
                    p.last_name,
                    p.positions,
                    p.attributes,
                    cyd.base_salary,
                    cyd.total_cap_hit,
                    cyd.signing_bonus_proration
                FROM player_contracts pc
                JOIN players p ON pc.player_id = p.player_id AND pc.dynasty_id = p.dynasty_id
                JOIN contract_year_details cyd ON pc.contract_id = cyd.contract_id
                WHERE pc.team_id = ?
                  AND pc.dynasty_id = ?
                  AND pc.is_active = 1
                  AND cyd.season_year = ?
                  AND cyd.base_salary >= ?
                  AND (pc.start_year + pc.contract_years - ?) >= ?
                ORDER BY cyd.base_salary DESC
            """

            years_remaining_min = self.MIN_YEARS_REMAINING
            years_remaining_formula = self._season

            # Query for next season since we're in offseason planning for next year
            next_season = self._season + 1

            cursor.execute(
                query,
                (
                    self._team_id,
                    self._dynasty_id,
                    next_season,  # Use next season for contract year details
                    self.MIN_BASE_SALARY,
                    years_remaining_formula,
                    years_remaining_min,
                ),
            )

            rows = cursor.fetchall()
            conn.close()

            # Convert rows to dicts
            candidates = []
            for row in rows:
                start_year = row["start_year"]
                years_remaining = (start_year + row["contract_years"]) - self._season

                # Calculate contract_year: which year of the contract we're restructuring
                # e.g., if contract started 2023 and next_season is 2026, contract_year = 4
                contract_year = next_season - start_year + 1

                # Parse player name from first_name + last_name
                name = f"{row['first_name']} {row['last_name']}"

                # Parse position from positions (may be JSON array or comma-separated)
                positions_str = row["positions"] or ""
                position = ""
                if positions_str:
                    # Try JSON array first (e.g., '["DEFENSIVE_END", "LINEBACKER"]')
                    if positions_str.startswith("["):
                        try:
                            positions_list = json.loads(positions_str)
                            position = positions_list[0] if positions_list else ""
                        except (json.JSONDecodeError, TypeError):
                            position = ""
                    else:
                        # Fall back to comma-separated (e.g., "DEFENSIVE_END,LINEBACKER")
                        positions_list = positions_str.split(",")
                        position = positions_list[0].strip() if positions_list else ""

                # Parse overall and age from attributes JSON
                try:
                    attributes = json.loads(row["attributes"]) if row["attributes"] else {}
                    overall = attributes.get("overall", 0)  # Will be extracted using utility later
                    age = attributes.get("age", 25)
                except (json.JSONDecodeError, TypeError):
                    overall = 0
                    age = 25

                candidates.append({
                    "contract_id": row["contract_id"],
                    "player_id": row["player_id"],
                    "team_id": row["team_id"],
                    "name": name,
                    "position": position,
                    "overall": overall,
                    "age": age,
                    "contract_years": row["contract_years"],
                    "years_remaining": years_remaining,
                    "start_year": start_year,
                    "contract_year": contract_year,  # Year of contract being restructured
                    "total_value": row["total_value"],
                    "signing_bonus": row["signing_bonus"],
                    "base_salary": row["base_salary"],
                    "current_cap_hit": row["total_cap_hit"],
                    "prorated_bonus": row["signing_bonus_proration"] or 0,
                })

            self._logger.debug(f"Found {len(candidates)} restructurable contracts")
            return candidates

        except Exception as e:
            self._logger.error(f"Error getting restructurable contracts: {e}")
            return []

    def _calculate_restructure_impact(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate cap impact of restructuring contract.

        Uses CapCalculator to determine savings and future impact.

        Args:
            candidate: Contract candidate dict

        Returns:
            Dict with cap_savings_current_year, annual_increase_future_years,
            dead_money_increase, new_proration, remaining_years
        """
        base_salary = candidate["base_salary"]
        years_remaining = candidate["years_remaining"]

        # Determine how much base salary to convert based on GM archetype
        # Higher risk_tolerance = convert more
        # Higher win_now = convert more
        conversion_factor = (
            0.5  # Base: convert 50%
            + (self._gm_archetype.risk_tolerance * 0.3)  # +0 to +30%
            + (self._gm_archetype.win_now_mentality * 0.2)  # +0 to +20%
        )
        conversion_factor = min(conversion_factor, 0.95)  # Cap at 95%

        base_to_convert = int(base_salary * conversion_factor)

        # Calculate impact using CapCalculator
        impact = self._cap_calculator.calculate_restructure_impact(
            base_salary_to_convert=base_to_convert,
            remaining_contract_years=years_remaining,
        )

        # Add the conversion amount to impact
        impact["base_salary_converted"] = base_to_convert

        return impact

    def _score_candidate(self, candidate: Dict[str, Any], cap_space: int) -> Dict[str, Any]:
        """
        Score candidate based on GM archetype and team situation.

        Args:
            candidate: Contract candidate dict
            cap_space: Available cap space

        Returns:
            Dict with score components
        """
        score = 0.0
        reasons = []

        # Cap pressure urgency (max +50)
        if cap_space <= self.CAP_EMERGENCY_THRESHOLD:
            score += 50
            reasons.append("emergency_cap_relief")
        elif cap_space < self.CAP_TIGHT_THRESHOLD:
            score += 30
            reasons.append("tight_cap_relief")
        elif cap_space < self.CAP_COMFORTABLE_THRESHOLD:
            score += 10
            reasons.append("proactive_cap_management")

        # Protected player bonus (max +30)
        if candidate["player_id"] in self._directives.protected_player_ids:
            score += 30 * self._gm_archetype.loyalty
            reasons.append("protected_player")

        # Star player bonus (max +25)
        overall = extract_overall_rating(candidate, default=0)
        if overall >= 90:
            score += 25 * self._gm_archetype.star_chasing
            reasons.append("star_player")
        elif overall >= 80:
            score += 15
            reasons.append("high_value_player")

        # Win-now bonus for veteran stars (max +20)
        if (
            self._gm_archetype.win_now_mentality >= 0.7
            and overall >= 85
            and candidate["age"] >= 27
        ):
            score += 20
            reasons.append("win_now_veteran")

        # Cap management proactive bonus (max +15)
        if self._gm_archetype.cap_management >= 0.7:
            score += 15
            reasons.append("proactive_cap_manager")

        # Position priority bonus (max +10)
        if candidate["position"] in self._directives.priority_positions:
            score += 10
            reasons.append("priority_position")

        return {
            "total_score": score,
            "reasons": reasons,
        }

    def _determine_tier(self, candidate: Dict[str, Any], cap_space: int) -> int:
        """
        Determine priority tier based on cap situation and player importance.

        Args:
            candidate: Contract candidate dict
            cap_space: Available cap space

        Returns:
            Tier number (1 = highest priority)
        """
        # Tier 1: Emergency (over cap)
        if cap_space <= self.CAP_EMERGENCY_THRESHOLD:
            return self.TIER_EMERGENCY

        # Tier 2: Protected player
        if candidate["player_id"] in self._directives.protected_player_ids:
            return self.TIER_PROTECTED

        # Tier 3: Star player (90+ OVR)
        overall = extract_overall_rating(candidate, default=0)
        if overall >= 90:
            return self.TIER_STAR

        # Tier 4: High-value player (80-89 OVR)
        if overall >= 80:
            return self.TIER_HIGH_VALUE

        # Tier 5: Proactive optimization
        return self.TIER_PROACTIVE

    def _create_proposal(
        self,
        candidate: Dict[str, Any],
        score_data: Dict[str, Any],
        impact: Dict[str, Any],
        cap_space: int,
        tier: int,
    ) -> PersistentGMProposal:
        """
        Create a PersistentGMProposal for the restructure.

        Args:
            candidate: Contract candidate dict
            score_data: Scoring data
            impact: Restructure impact data
            cap_space: Available cap space
            tier: Priority tier

        Returns:
            PersistentGMProposal object
        """
        player_id = candidate["player_id"]
        name = candidate["name"]
        position = candidate["position"]
        overall = candidate["overall"]
        age = candidate["age"]
        current_cap_hit = candidate["current_cap_hit"]
        contract_id = candidate["contract_id"]
        contract_year = candidate["contract_year"]

        # Calculate proposed cap hit
        cap_savings = impact["cap_savings_current_year"]
        proposed_cap_hit = current_cap_hit - cap_savings

        # Create details using helper
        details = create_restructure_details(
            player_name=name,
            position=position,
            overall=overall,
            age=age,
            current_cap_hit=current_cap_hit,
            proposed_cap_hit=proposed_cap_hit,
            cap_savings=cap_savings,
            dead_money_increase=impact["dead_money_increase"],
            base_salary_converted=impact["base_salary_converted"],
            years_remaining=impact["remaining_years"],
            contract_id=contract_id,
            contract_year=contract_year,
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(candidate, impact, cap_space, score_data)

        # Calculate confidence
        # Higher tier = higher confidence
        # Higher cap_management = higher confidence
        base_confidence = 0.6
        tier_bonus = (6 - tier) * 0.05  # Tier 1 = +0.25, Tier 5 = +0.05
        archetype_bonus = self._gm_archetype.cap_management * 0.2
        confidence = min(0.95, max(0.5, base_confidence + tier_bonus + archetype_bonus))

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_RESTRUCTURE",
            proposal_type=ProposalType.RESTRUCTURE,
            subject_player_id=str(player_id),
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=tier,
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )

    def _generate_reasoning(
        self,
        candidate: Dict[str, Any],
        impact: Dict[str, Any],
        cap_space: int,
        score_data: Dict[str, Any],
    ) -> str:
        """
        Generate contextual reasoning based on archetype and situation.

        Args:
            candidate: Contract candidate dict
            impact: Restructure impact data
            cap_space: Available cap space
            score_data: Scoring data

        Returns:
            Human-readable reasoning string
        """
        name = candidate["name"]
        position = candidate["position"]
        overall = candidate["overall"]
        age = candidate["age"]
        cap_savings = impact["cap_savings_current_year"]
        dead_money_increase = impact["dead_money_increase"]
        base_converted = impact["base_salary_converted"]
        years_remaining = impact["remaining_years"]

        # Format values
        savings_str = f"${cap_savings / 1_000_000:.1f}M"
        converted_str = f"${base_converted / 1_000_000:.1f}M"
        dead_money_str = f"${dead_money_increase / 1_000_000:.1f}M"
        cap_space_str = f"${cap_space / 1_000_000:.1f}M" if cap_space >= 0 else f"-${abs(cap_space) / 1_000_000:.1f}M"

        reasons = score_data.get("reasons", [])

        # Emergency tier (Tier 1)
        if "emergency_cap_relief" in reasons:
            return (
                f"We're over the cap by ${abs(cap_space) / 1_000_000:.1f}M and MUST create space to get compliant. "
                f"Restructuring {name}'s contract saves {savings_str} immediately by converting "
                f"{converted_str} of base salary to bonus prorated over {years_remaining} years. "
                f"This increases future dead money by {dead_money_str}, but we have no choice right now."
            )

        # Protected player + high loyalty (Tier 2)
        if "protected_player" in reasons and self._gm_archetype.loyalty >= 0.7:
            return (
                f"{name} is a protected player you've identified as core to our future. "
                f"At {overall} OVR, he's valuable, and this restructure shows our commitment while "
                f"creating {savings_str} in cap relief. We'll convert {converted_str} of base salary "
                f"to bonus, spreading the hit over {years_remaining} years. The added {dead_money_str} "
                f"in future dead money is worth keeping him long-term."
            )

        # Star player + star chasing (Tier 3)
        if "star_player" in reasons and self._gm_archetype.star_chasing >= 0.7:
            return (
                f"{name} ({position}, {overall} OVR) is an elite talent we're building around. "
                f"Restructuring his deal frees {savings_str} immediately to improve the roster, "
                f"which is critical for maximizing our window with a player of his caliber. "
                f"Converting {converted_str} to bonus adds {dead_money_str} in future risk, "
                f"but elite players are worth the investment."
            )

        # Win-now mentality (Tier 3-4)
        if self._gm_archetype.win_now_mentality >= 0.7:
            return (
                f"With our championship window open, we need to maximize the roster NOW. "
                f"Restructuring {name}'s contract ({overall} OVR, age {age}) saves {savings_str} "
                f"this year by converting {converted_str} to bonus. Yes, it adds {dead_money_str} "
                f"in future dead money over {years_remaining} years, but winning the Super Bowl "
                f"is worth the risk. Current cap: {cap_space_str}."
            )

        # Cap management proactive (Tier 5)
        if self._gm_archetype.cap_management >= 0.7:
            return (
                f"Smart cap move to create flexibility. {name} ({position}, {overall} OVR) "
                f"has {years_remaining} years left, making this a good restructure candidate. "
                f"Converting {converted_str} of base to bonus saves {savings_str} now "
                f"while only adding {dead_money_str} in future obligations. This gives us "
                f"room to improve the roster without compromising future flexibility. "
                f"Current cap: {cap_space_str}."
            )

        # Risk tolerance (aggressive restructures)
        if self._gm_archetype.risk_tolerance >= 0.7:
            return (
                f"This is a calculated risk I'm willing to take. Restructuring {name}'s deal "
                f"saves {savings_str} immediately by converting {converted_str} to prorated bonus. "
                f"It increases future dead money by {dead_money_str}, but the upside of having "
                f"that cap space NOW to make moves outweighs the risk. {name} ({overall} OVR, "
                f"{position}) is worth keeping, and this keeps us competitive. Cap space: {cap_space_str}."
            )

        # Default reasoning (balanced approach)
        return (
            f"Restructuring {name}'s contract creates {savings_str} in immediate cap relief. "
            f"At {overall} OVR and age {age}, he's a solid contributor, and this move "
            f"helps our cap situation (currently {cap_space_str}) without cutting talent. "
            f"Converting {converted_str} of base salary to bonus spreads the cost over "
            f"{years_remaining} years, adding {dead_money_str} in potential dead money. "
            f"It's a standard cap management technique."
        )
