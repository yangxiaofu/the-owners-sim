"""Player Preference Engine for evaluating team offers.

Evaluates team/contract offers based on player preferences and personas,
calculates acceptance probabilities, and generates player concerns.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from .player_persona import PlayerPersona, PersonaType
from .team_attractiveness import TeamAttractiveness


@dataclass
class ContractOffer:
    """Represents a contract offer to a player."""

    team_id: int
    aav: int  # Average annual value in dollars
    total_value: int
    years: int
    guaranteed: int
    signing_bonus: int = 0

    # Context
    market_aav: int = 0  # Market value AAV for comparison
    role: str = "rotational"  # 'starter', 'rotational', 'backup'

    @property
    def offer_vs_market(self) -> float:
        """Ratio of offer to market value (1.0 = at market)."""
        if self.market_aav <= 0:
            return 1.0
        return self.aav / self.market_aav

    @property
    def guaranteed_percentage(self) -> float:
        """Percentage of contract that is guaranteed."""
        if self.total_value <= 0:
            return 0.0
        return self.guaranteed / self.total_value


@dataclass
class OfferEvaluation:
    """Result of evaluating an offer."""

    team_id: int
    team_score: int
    acceptance_probability: float
    concerns: List[str]
    offer: ContractOffer


class PlayerPreferenceEngine:
    """Evaluates team offers based on player preferences.

    Responsibilities:
    - Calculate weighted team scores based on persona
    - Apply persona-specific bonuses
    - Calculate acceptance probability with money override
    - Generate player concerns about teams
    """

    def __init__(self):
        """Initialize the preference engine."""
        self._logger = logging.getLogger(__name__)

    # -------------------- Score Calculation --------------------

    def _calculate_money_score(self, offer: ContractOffer) -> int:
        """Score based on offer vs market value (0-100)."""
        ratio = offer.offer_vs_market

        if ratio >= 1.2:
            return 100
        elif ratio >= 1.0:
            # Linear interpolation: 80 at 1.0, 100 at 1.2
            return int(80 + (ratio - 1.0) * 100)
        elif ratio >= 0.8:
            # Linear interpolation: 40 at 0.8, 80 at 1.0
            return int(40 + (ratio - 0.8) * 200)
        else:
            # Linear interpolation: 0 at 0.0, 40 at 0.8
            return int(ratio / 0.8 * 40)

    def _calculate_winning_score(self, team: TeamAttractiveness) -> int:
        """Score based on team's contender status (0-100)."""
        return team.contender_score

    def _calculate_location_score(
        self,
        persona: PlayerPersona,
        team: TeamAttractiveness
    ) -> int:
        """Score based on location factors (0-100).

        Components:
        - Tax advantage: 0-30 points
        - Weather: 0-30 points
        - Home state: 40 points (birthplace) or 20 points (college)
        """
        score = 0.0

        # Tax advantage (0-30 points)
        score += team.tax_advantage_score * 0.3

        # Weather (0-30 points)
        score += team.weather_score * 0.3

        # Proximity to home (0-40 points)
        if persona.birthplace_state and team.state == persona.birthplace_state:
            score += 40
        elif persona.college_state and team.state == persona.college_state:
            score += 20

        return int(min(100, score))

    def _calculate_playing_time_score(self, offer: ContractOffer) -> int:
        """Score based on expected role (0-100)."""
        role_scores = {
            "starter": 100,
            "rotational": 60,
            "backup": 30,
        }
        return role_scores.get(offer.role, 50)

    def _calculate_loyalty_score(
        self,
        is_current_team: bool,
        is_drafting_team: bool
    ) -> int:
        """Score based on loyalty to current/drafting team (0-100)."""
        score = 0
        if is_current_team:
            score += 50
        if is_drafting_team:
            score += 50
        return min(100, score)

    def _calculate_market_score(self, team: TeamAttractiveness) -> int:
        """Score based on market size (0-100)."""
        return team.market_size

    # -------------------- Persona Bonuses --------------------

    def _apply_persona_bonuses(
        self,
        persona: PlayerPersona,
        team: TeamAttractiveness,
        offer: ContractOffer,
        money_score: int,
        winning_score: int,
        location_score: int,
        playing_time_score: int,
        loyalty_score: int,
        market_score: int
    ) -> Tuple[int, int, int, int, int, int]:
        """Apply persona-specific bonuses to scores."""

        if persona.persona_type == PersonaType.RING_CHASER:
            # +20 to winning score if team is a contender
            if team.contender_score > 70:
                winning_score = min(100, winning_score + 20)

        elif persona.persona_type == PersonaType.HOMETOWN_HERO:
            # +30 to location if in home state
            if team.state == persona.birthplace_state:
                location_score = min(100, location_score + 30)

        elif persona.persona_type == PersonaType.MONEY_FIRST:
            # Boost money score by 10 (money_importance handled in weighting)
            money_score = min(100, money_score + 10)

        elif persona.persona_type == PersonaType.BIG_MARKET:
            # +25 to market score if large market
            if team.market_size > 70:
                market_score = min(100, market_score + 25)

        elif persona.persona_type == PersonaType.SMALL_MARKET:
            # +25 to market score if small market
            if team.market_size < 40:
                market_score = min(100, market_score + 25)

        elif persona.persona_type == PersonaType.LEGACY_BUILDER:
            # +40 to loyalty score
            loyalty_score = min(100, loyalty_score + 40)

        elif persona.persona_type == PersonaType.COMPETITOR:
            # +30 if starter, -30 if backup
            if offer.role == "starter":
                playing_time_score = min(100, playing_time_score + 30)
            elif offer.role == "backup":
                playing_time_score = max(0, playing_time_score - 30)

        # SYSTEM_FIT bonus deferred (requires coaching system)

        return (
            money_score,
            winning_score,
            location_score,
            playing_time_score,
            loyalty_score,
            market_score,
        )

    # -------------------- Core Methods --------------------

    def calculate_team_score(
        self,
        persona: PlayerPersona,
        team: TeamAttractiveness,
        offer: ContractOffer,
        is_current_team: bool = False,
        is_drafting_team: bool = False
    ) -> int:
        """Calculate weighted team score based on persona preferences (0-100)."""

        # Calculate individual factor scores
        money_score = self._calculate_money_score(offer)
        winning_score = self._calculate_winning_score(team)
        location_score = self._calculate_location_score(persona, team)
        playing_time_score = self._calculate_playing_time_score(offer)
        loyalty_score = self._calculate_loyalty_score(is_current_team, is_drafting_team)
        market_score = self._calculate_market_score(team)

        # Apply persona-specific bonuses BEFORE weighting
        (
            money_score,
            winning_score,
            location_score,
            playing_time_score,
            loyalty_score,
            market_score,
        ) = self._apply_persona_bonuses(
            persona,
            team,
            offer,
            money_score,
            winning_score,
            location_score,
            playing_time_score,
            loyalty_score,
            market_score,
        )

        # Get weights from persona (already 0-100)
        weights = {
            "money": persona.money_importance,
            "winning": persona.winning_importance,
            "location": persona.location_importance,
            "playing_time": persona.playing_time_importance,
            "loyalty": persona.loyalty_importance,
            "market": persona.market_size_importance,
        }

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight == 0:
            total_weight = 1  # Prevent division by zero

        # Calculate weighted score
        final_score = (
            (weights["money"] / total_weight) * money_score
            + (weights["winning"] / total_weight) * winning_score
            + (weights["location"] / total_weight) * location_score
            + (weights["playing_time"] / total_weight) * playing_time_score
            + (weights["loyalty"] / total_weight) * loyalty_score
            + (weights["market"] / total_weight) * market_score
        )

        return int(min(100, max(0, final_score)))

    def calculate_acceptance_probability(
        self,
        persona: PlayerPersona,
        team_score: int,
        offer_vs_market: float
    ) -> float:
        """Calculate probability player accepts this offer (0.0-1.0).

        Money Override Rule:
        - offer >= 120% market: 95% acceptance regardless of preferences
        - offer >= 110% market: +30% acceptance bonus
        - offer < 80% market: -40% acceptance penalty
        - offer < 90% market: -15% acceptance penalty
        """
        # Base probability from team score (0-100 -> 0.0-1.0)
        base_prob = team_score / 100

        # Money Override (takes precedence)
        if offer_vs_market >= 1.20:
            return 0.95  # Almost always accept big money
        elif offer_vs_market >= 1.10:
            base_prob += 0.30
        elif offer_vs_market < 0.80:
            base_prob -= 0.40
        elif offer_vs_market < 0.90:
            base_prob -= 0.15

        # Money First persona always has high acceptance for good money
        if persona.persona_type == PersonaType.MONEY_FIRST:
            if offer_vs_market >= 1.0:
                base_prob = max(base_prob, 0.85)

        # Clamp to valid range
        return max(0.05, min(0.95, base_prob))

    def get_concerns(
        self,
        persona: PlayerPersona,
        team: TeamAttractiveness,
        offer: ContractOffer
    ) -> List[str]:
        """Get list of player concerns about this team/offer."""
        concerns = []

        # Winning concerns
        if persona.winning_importance > 60 and team.contender_score < 40:
            concerns.append("Concerned about team's recent playoff history")

        # Location concerns
        if persona.persona_type == PersonaType.HOMETOWN_HERO:
            if persona.birthplace_state and team.state != persona.birthplace_state:
                concerns.append("Would prefer to play closer to home")

        # Market size concerns
        if persona.persona_type == PersonaType.BIG_MARKET:
            if team.market_size < 50:
                concerns.append("Prefers a larger market for endorsements")
        elif persona.persona_type == PersonaType.SMALL_MARKET:
            if team.market_size > 70:
                concerns.append("May feel overwhelmed by media scrutiny")

        # Playing time concerns
        if persona.persona_type == PersonaType.COMPETITOR:
            if offer.role == "backup":
                concerns.append("Wants guaranteed playing time")

        # Money concerns
        if offer.offer_vs_market < 0.90:
            if persona.persona_type == PersonaType.MONEY_FIRST:
                concerns.append("Expects top dollar")
            elif persona.money_importance > 70:
                concerns.append("May want a more competitive offer")

        # Loyalty concerns
        if persona.persona_type == PersonaType.LEGACY_BUILDER:
            concerns.append("Values long-term commitment")

        # Tax concerns
        if persona.money_importance > 60 and team.state_income_tax_rate > 0.08:
            concerns.append("May factor in state income taxes")

        return concerns

    def evaluate_all_offers(
        self,
        persona: PlayerPersona,
        offers: List[Tuple[TeamAttractiveness, ContractOffer]],
        current_team_id: Optional[int] = None
    ) -> List[OfferEvaluation]:
        """Rank all offers by preference.

        Args:
            persona: Player's persona
            offers: List of (team, offer) tuples
            current_team_id: Player's current team (if any)

        Returns:
            List of OfferEvaluation sorted by team_score (highest first)
        """
        evaluations = []

        for team, offer in offers:
            is_current = team.team_id == current_team_id
            is_drafting = team.team_id == persona.drafting_team_id

            score = self.calculate_team_score(
                persona, team, offer, is_current, is_drafting
            )
            prob = self.calculate_acceptance_probability(
                persona, score, offer.offer_vs_market
            )
            concerns = self.get_concerns(persona, team, offer)

            evaluations.append(
                OfferEvaluation(
                    team_id=team.team_id,
                    team_score=score,
                    acceptance_probability=prob,
                    concerns=concerns,
                    offer=offer,
                )
            )

        # Sort by team score (highest first)
        evaluations.sort(key=lambda e: e.team_score, reverse=True)
        return evaluations

    def should_accept_offer(
        self,
        persona: PlayerPersona,
        team: TeamAttractiveness,
        offer: ContractOffer,
        is_current_team: bool = False,
        is_drafting_team: bool = False
    ) -> Tuple[bool, float, List[str]]:
        """Determine if player accepts this offer.

        Args:
            persona: Player's persona
            team: Team making the offer
            offer: Contract details
            is_current_team: Whether this is player's current team
            is_drafting_team: Whether this is the team that drafted the player

        Returns:
            Tuple of (accepted, probability, concerns)
        """
        score = self.calculate_team_score(
            persona, team, offer, is_current_team, is_drafting_team
        )
        probability = self.calculate_acceptance_probability(
            persona, score, offer.offer_vs_market
        )
        concerns = self.get_concerns(persona, team, offer)

        # Roll the dice
        accepted = random.random() < probability

        return accepted, probability, concerns
