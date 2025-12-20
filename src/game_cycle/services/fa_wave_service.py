"""
FA Wave Service for multi-wave free agency management.

Part of Milestone 8: Free Agency Depth - Tollgate 2.
Manages wave progression, offer lifecycle, and player decision resolution.
"""

import logging
import random
from typing import Dict, List, Any, Optional

from src.game_cycle.database.fa_wave_state_api import FAWaveStateAPI, WAVE_CONFIGS


class FAWaveService:
    """
    Manages multi-wave free agency with offer windows.

    Features:
    - 5-wave system: Legal Tampering → Wave 1-3 → Post-Draft
    - Offer submission and withdrawal
    - AI offer generation based on team needs
    - Surprise signings (AI can sign players during window)
    - Offer resolution using PlayerPreferenceEngine
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the FA Wave Service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded dependencies
        self._offers_api = None
        self._wave_state_api = None
        self._fa_service = None
        self._preference_engine = None

    # -------------------------------------------------------------------------
    # Lazy-loading methods
    # -------------------------------------------------------------------------

    def _get_offers_api(self):
        """Lazy-load PendingOffersAPI."""
        if self._offers_api is None:
            from src.game_cycle.database.pending_offers_api import PendingOffersAPI
            self._offers_api = PendingOffersAPI(self._db_path)
        return self._offers_api

    def _get_wave_state_api(self) -> FAWaveStateAPI:
        """Lazy-load FAWaveStateAPI."""
        if self._wave_state_api is None:
            self._wave_state_api = FAWaveStateAPI(self._db_path)
        return self._wave_state_api

    def _get_fa_service(self):
        """Lazy-load FreeAgencyService for player data and signing."""
        if self._fa_service is None:
            from src.game_cycle.services.free_agency_service import FreeAgencyService
            self._fa_service = FreeAgencyService(
                self._db_path, self._dynasty_id, self._season
            )
        return self._fa_service

    def _get_preference_engine(self):
        """Lazy-load PlayerPreferenceEngine."""
        if self._preference_engine is None:
            from src.player_management.preference_engine import PlayerPreferenceEngine
            self._preference_engine = PlayerPreferenceEngine()
        return self._preference_engine

    # -------------------------------------------------------------------------
    # Wave State Management
    # -------------------------------------------------------------------------

    def get_wave_state(self) -> Dict[str, Any]:
        """
        Get current wave state with derived info.

        Returns:
            Dict with wave state including wave_name, days_in_wave, signing_allowed.
            Initializes state if not found.
        """
        api = self._get_wave_state_api()
        state = api.get_wave_state(self._dynasty_id, self._season)
        if not state:
            state = api.initialize_wave_state(self._dynasty_id, self._season)
        return state

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance to next day within current wave.

        Returns:
            Updated wave state
        """
        api = self._get_wave_state_api()
        return api.advance_day(self._dynasty_id, self._season)

    def advance_wave(self) -> Optional[Dict[str, Any]]:
        """
        Advance to next wave (resets to day 1).

        Returns:
            Updated wave state, or None if FA is complete
        """
        api = self._get_wave_state_api()
        return api.advance_wave(self._dynasty_id, self._season)

    def enable_post_draft_wave(self) -> Dict[str, Any]:
        """
        Enable wave 4 after draft completes.

        Returns:
            Updated wave state
        """
        api = self._get_wave_state_api()
        return api.enable_post_draft_wave(self._dynasty_id, self._season)

    def is_fa_complete(self) -> bool:
        """Check if all FA waves are complete (including post-draft)."""
        api = self._get_wave_state_api()
        return api.is_fa_complete(self._dynasty_id, self._season)

    # -------------------------------------------------------------------------
    # Player Filtering
    # -------------------------------------------------------------------------

    def get_available_players_for_wave(
        self,
        wave: Optional[int] = None,
        user_team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get free agents filtered by OVR for current wave tier.

        Args:
            wave: Wave number (0-4). Uses current wave if not specified.
            user_team_id: User's team ID (for checking user's offers)

        Returns:
            List of player dicts with offer status included
        """
        if wave is None:
            state = self.get_wave_state()
            wave = state["current_wave"]

        config = WAVE_CONFIGS.get(wave, WAVE_CONFIGS[0])
        min_ovr = config["min_ovr"]
        max_ovr = config["max_ovr"]

        fa_service = self._get_fa_service()
        all_fas = fa_service.get_available_free_agents()

        # Filter by OVR tier
        filtered = [
            p for p in all_fas
            if min_ovr <= p.get("overall", 0) <= max_ovr
        ]

        # Add offer status for each player
        offers_api = self._get_offers_api()
        for player in filtered:
            offers = offers_api.get_offers_by_player(
                self._dynasty_id, player["player_id"], status="pending"
            )
            player["pending_offer_count"] = len(offers)
            player["has_user_offer"] = False
            if user_team_id is not None:
                player["has_user_offer"] = any(
                    o["offering_team_id"] == user_team_id for o in offers
                )

        return filtered

    # -------------------------------------------------------------------------
    # Offer Submission
    # -------------------------------------------------------------------------

    def submit_offer(
        self,
        player_id: int,
        team_id: int,
        aav: int,
        years: int,
        guaranteed: int,
        signing_bonus: int = 0
    ) -> Dict[str, Any]:
        """
        Submit an offer to a free agent (doesn't sign immediately).

        Args:
            player_id: Player ID to offer
            team_id: Team ID making the offer
            aav: Average annual value in dollars
            years: Contract length (1-7)
            guaranteed: Guaranteed money in dollars
            signing_bonus: Optional signing bonus in dollars

        Returns:
            Dict with success, offer_id, wave, decision_deadline, or error
        """
        state = self.get_wave_state()
        wave = state["current_wave"]

        # Validate signing is allowed
        if not state["signing_allowed"]:
            return {
                "success": False,
                "error": "Offers not allowed in Legal Tampering (Wave 0)"
            }

        # Check for duplicate offer
        offers_api = self._get_offers_api()
        existing = offers_api.check_existing_offer(
            self._dynasty_id, self._season, wave, player_id, team_id
        )
        if existing:
            return {
                "success": False,
                "error": "Already have pending offer for this player"
            }

        # Validate cap space (use season + 1 for offseason)
        fa_service = self._get_fa_service()
        cap_space = fa_service.get_team_cap_space(team_id)
        if aav > cap_space:
            return {
                "success": False,
                "error": f"Insufficient cap space: ${cap_space:,} available"
            }

        # Calculate decision deadline (end of wave)
        config = WAVE_CONFIGS.get(wave, WAVE_CONFIGS[1])
        deadline = config["days"]

        # Create the offer
        total_value = aav * years
        offer_id = offers_api.create_offer(
            dynasty_id=self._dynasty_id,
            season=self._season,
            wave=wave,
            player_id=player_id,
            offering_team_id=team_id,
            aav=aav,
            total_value=total_value,
            years=years,
            guaranteed=guaranteed,
            signing_bonus=signing_bonus,
            decision_deadline=deadline
        )

        self._logger.info(
            f"Offer created: Team {team_id} → Player {player_id}, "
            f"${aav:,}/yr for {years} years (offer_id={offer_id})"
        )

        return {
            "success": True,
            "offer_id": offer_id,
            "wave": wave,
            "decision_deadline": deadline
        }

    def withdraw_offer(self, offer_id: int) -> bool:
        """
        Withdraw a pending offer.

        Args:
            offer_id: Offer ID to withdraw

        Returns:
            True if withdrawn successfully
        """
        result = self._get_offers_api().withdraw_offer(offer_id)
        if result:
            self._logger.info(f"Offer {offer_id} withdrawn")
        return result

    def get_team_pending_offers(
        self,
        team_id: int,
        status: Optional[str] = "pending"
    ) -> List[Dict[str, Any]]:
        """
        Get all pending offers for a team.

        Args:
            team_id: Team ID
            status: Optional status filter

        Returns:
            List of offer dicts
        """
        return self._get_offers_api().get_offers_by_team(
            self._dynasty_id, team_id, status=status
        )

    def get_player_offers(
        self,
        player_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all offers for a specific player.

        Args:
            player_id: Player ID
            status: Optional status filter

        Returns:
            List of offer dicts, ordered by AAV descending
        """
        return self._get_offers_api().get_offers_by_player(
            self._dynasty_id, player_id, status=status
        )

    # -------------------------------------------------------------------------
    # AI Offer Generation
    # -------------------------------------------------------------------------

    def generate_ai_offers(
        self,
        user_team_id: int,
        max_offers_per_team: int = 3
    ) -> Dict[str, Any]:
        """
        Have AI teams submit offers for players in current wave.

        AI targeting logic:
        1. Get positional needs for each AI team
        2. Filter to players in current wave tier
        3. Evaluate interest before offering
        4. Skip low-interest players
        5. Generate market-appropriate offers

        Args:
            user_team_id: User's team ID (to skip)
            max_offers_per_team: Maximum pending offers per AI team

        Returns:
            Dict with offers_made count and events list
        """
        state = self.get_wave_state()
        wave = state["current_wave"]

        if not state["signing_allowed"]:
            return {"offers_made": 0, "events": []}

        available_players = self.get_available_players_for_wave(wave)
        fa_service = self._get_fa_service()
        offers_api = self._get_offers_api()

        offers_made = 0
        events = []

        # Process each AI team
        for team_id in range(1, 33):
            if team_id == user_team_id:
                continue

            # Count existing offers this wave
            team_offers = offers_api.get_offers_by_team(
                self._dynasty_id, team_id, status="pending"
            )
            if len(team_offers) >= max_offers_per_team:
                continue

            # Get positional needs
            from database.player_roster_api import PlayerRosterAPI
            roster_api = PlayerRosterAPI(self._db_path)
            needs = fa_service._get_team_positional_needs(team_id, roster_api)
            if not needs:
                continue

            # Find best available player matching needs
            for player in available_players:
                position = player.get("position", "").lower()
                if not any(position == need.lower() for need in needs):
                    continue

                # Check interest level
                interest = fa_service.evaluate_player_interest(
                    player["player_id"], team_id, player
                )
                if interest["interest_level"] in ["very_low", "low"]:
                    continue

                # Already have offer?
                existing = offers_api.check_existing_offer(
                    self._dynasty_id, self._season, wave,
                    player["player_id"], team_id
                )
                if existing:
                    continue

                # Check cap space
                cap_space = fa_service.get_team_cap_space(team_id)
                market_aav = player.get("estimated_aav", 5_000_000)
                if market_aav > cap_space:
                    continue

                # Generate competitive offer (market value * 1.0-1.15)
                multiplier = 1.0 + (random.random() * 0.15)
                offer_aav = int(market_aav * multiplier)

                # Ensure offer fits in cap
                offer_aav = min(offer_aav, cap_space)

                result = self.submit_offer(
                    player_id=player["player_id"],
                    team_id=team_id,
                    aav=offer_aav,
                    years=random.choice([2, 3, 4]),
                    guaranteed=int(offer_aav * random.uniform(0.4, 0.6)),
                    signing_bonus=int(offer_aav * 0.1)
                )

                if result.get("success"):
                    offers_made += 1
                    events.append(
                        f"Team {team_id} submitted offer to {player['name']}"
                    )
                    break  # One offer per team per cycle

        self._logger.info(f"AI generated {offers_made} offers in wave {wave}")
        return {"offers_made": offers_made, "events": events}

    # -------------------------------------------------------------------------
    # Surprise Signings
    # -------------------------------------------------------------------------

    def process_surprise_signings(
        self,
        user_team_id: int,
        probability: float = 0.20
    ) -> List[Dict[str, Any]]:
        """
        AI teams may sign players early, stealing from user's targets.

        Only triggers if:
        1. AI team has pending offer on a player
        2. User ALSO has pending offer on same player
        3. Random check passes (20% default)

        Args:
            user_team_id: User's team ID
            probability: Probability of surprise signing (0.0-1.0)

        Returns:
            List of surprise signing dicts with player_id, player_name, team_id, aav
        """
        surprises = []
        offers_api = self._get_offers_api()
        fa_service = self._get_fa_service()

        # Get players with user offers
        user_offers = offers_api.get_offers_by_team(
            self._dynasty_id, user_team_id, status="pending"
        )
        user_player_ids = {o["player_id"] for o in user_offers}

        if not user_player_ids:
            return surprises

        # Check each player user has offered
        for player_id in user_player_ids:
            # Get all offers for this player
            all_offers = offers_api.get_offers_by_player(
                self._dynasty_id, player_id, status="pending"
            )

            # Find AI offers
            ai_offers = [
                o for o in all_offers
                if o["offering_team_id"] != user_team_id
            ]
            if not ai_offers:
                continue

            # Random check for surprise signing
            if random.random() >= probability:
                continue

            # Pick highest AAV AI offer
            best_ai_offer = max(ai_offers, key=lambda x: x["aav"])

            # Execute the signing via FreeAgencyService
            result = fa_service.sign_free_agent(
                player_id=player_id,
                team_id=best_ai_offer["offering_team_id"],
                skip_preference_check=False  # Still check preferences
            )

            if result.get("success"):
                # Mark the winning offer as 'surprise'
                offers_api.update_offer_status(
                    best_ai_offer["offer_id"], "surprise"
                )

                # Reject all other offers for this player
                other_offer_ids = [
                    o["offer_id"] for o in all_offers
                    if o["offer_id"] != best_ai_offer["offer_id"]
                ]
                if other_offer_ids:
                    offers_api.bulk_update_status(other_offer_ids, "rejected")

                # Extract player data from contract_details for headline generation
                contract_details = result.get("contract_details", {})

                surprise_info = {
                    "player_id": player_id,
                    "player_name": result.get("player_name", f"Player {player_id}"),
                    "team_id": best_ai_offer["offering_team_id"],
                    "aav": best_ai_offer["aav"],
                    "position": contract_details.get("position", ""),
                    "overall": contract_details.get("overall", 0),
                    "age": contract_details.get("age", 0),
                }
                surprises.append(surprise_info)

                self._logger.info(
                    f"Surprise signing: {surprise_info['player_name']} "
                    f"signed by Team {surprise_info['team_id']}"
                )

        return surprises

    # -------------------------------------------------------------------------
    # Offer Resolution
    # -------------------------------------------------------------------------

    def resolve_wave_offers(
        self,
        user_team_id: Optional[int] = None,
        fa_guidance: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Resolve all pending offers at wave end.
        Each player chooses best offer based on preferences.

        Args:
            user_team_id: User's team ID (for budget stance modifier)
            fa_guidance: Owner's FA guidance (for budget stance modifier)

        Returns:
            Dict with signings, rejections, no_accepts lists and total_resolved count
        """
        offers_api = self._get_offers_api()
        state = self.get_wave_state()
        wave = state["current_wave"]

        # Get all players with pending offers
        players_with_offers = offers_api.get_players_with_pending_offers(
            self._dynasty_id, self._season, wave
        )

        signings = []
        rejections = []
        no_accepts = []

        for player_id in players_with_offers:
            result = self._resolve_player_offers(
                player_id,
                user_team_id=user_team_id,
                fa_guidance=fa_guidance
            )

            if result["outcome"] == "signed":
                signings.append(result)
            elif result["outcome"] == "rejected_all":
                no_accepts.append(result)
            elif result["outcome"] == "signing_failed":
                rejections.append(result)

        self._logger.info(
            f"Wave {wave} resolved: {len(signings)} signed, "
            f"{len(no_accepts)} rejected all offers, {len(rejections)} failed"
        )

        return {
            "signings": signings,
            "rejections": rejections,
            "no_accepts": no_accepts,
            "total_resolved": len(players_with_offers)
        }

    def _resolve_player_offers(
        self,
        player_id: int,
        user_team_id: Optional[int] = None,
        fa_guidance: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Resolve offers for a single player using PreferenceEngine.

        Process:
        1. Get all pending offers
        2. Score each offer using calculate_team_score()
        3. Sort by score descending
        4. Check acceptance probability for top offer
        5. If accepted, sign contract; else try next

        Args:
            player_id: Player ID to resolve offers for
            user_team_id: User's team ID (for budget stance modifier)
            fa_guidance: Owner's FA guidance (for budget stance modifier)

        Returns:
            Dict with player_id, outcome, and relevant details
        """
        offers_api = self._get_offers_api()
        fa_service = self._get_fa_service()
        pref_engine = self._get_preference_engine()

        offers = offers_api.get_offers_by_player(
            self._dynasty_id, player_id, status="pending"
        )

        if not offers:
            return {"player_id": player_id, "outcome": "no_offers"}

        # Get player persona
        persona_service = fa_service._get_persona_service()
        persona = persona_service.get_persona(player_id)

        if not persona:
            # Accept highest AAV if no persona
            best_offer = max(offers, key=lambda x: x["aav"])
            return self._accept_offer(
                best_offer,
                user_team_id=user_team_id,
                fa_guidance=fa_guidance
            )

        # Score each offer
        scored_offers = []
        for offer in offers:
            try:
                # Get team attractiveness
                attr_service = fa_service._get_attractiveness_service()
                team_attr = attr_service.get_team_attractiveness(
                    offer["offering_team_id"]
                )

                # Build ContractOffer
                from src.player_management.preference_engine import ContractOffer
                contract_offer = ContractOffer(
                    team_id=offer["offering_team_id"],
                    aav=offer["aav"],
                    total_value=offer["total_value"],
                    years=offer["years"],
                    guaranteed=offer["guaranteed"],
                    signing_bonus=offer["signing_bonus"],
                    market_aav=offer.get("market_aav", offer["aav"]),
                    role="starter" if offer["aav"] > 10_000_000 else "rotational"
                )

                # Calculate score
                score = pref_engine.calculate_team_score(
                    persona=persona,
                    team=team_attr,
                    offer=contract_offer,
                    is_current_team=False,
                    is_drafting_team=(
                        offer["offering_team_id"] == persona.drafting_team_id
                    )
                )

                # Calculate acceptance probability
                prob = pref_engine.calculate_acceptance_probability(
                    persona=persona,
                    team_score=score,
                    offer_vs_market=contract_offer.offer_vs_market
                )

                scored_offers.append({
                    "offer": offer,
                    "score": score,
                    "probability": prob
                })

            except Exception as e:
                self._logger.warning(
                    f"Failed to score offer {offer['offer_id']}: {e}"
                )
                # Still include with default score
                scored_offers.append({
                    "offer": offer,
                    "score": 50,
                    "probability": 0.5
                })

        # Sort by score descending
        scored_offers.sort(key=lambda x: x["score"], reverse=True)

        # Try to accept offers in order of preference
        for scored in scored_offers:
            if random.random() < scored["probability"]:
                return self._accept_offer(
                    scored["offer"],
                    user_team_id=user_team_id,
                    fa_guidance=fa_guidance
                )

        # All rejected - player stays free agent
        offer_ids = [o["offer_id"] for o in offers]
        offers_api.bulk_update_status(offer_ids, "rejected")

        return {
            "player_id": player_id,
            "outcome": "rejected_all",
            "offers_rejected": len(offers)
        }

    def _accept_offer(
        self,
        offer: Dict[str, Any],
        user_team_id: Optional[int] = None,
        fa_guidance: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Accept an offer and create the contract.

        Args:
            offer: Offer dict to accept
            user_team_id: User's team ID (for budget stance modifier)
            fa_guidance: Owner's FA guidance (for budget stance modifier)

        Returns:
            Dict with outcome and signing details
        """
        offers_api = self._get_offers_api()
        fa_service = self._get_fa_service()

        # Apply budget stance modifier only for user team
        guidance_to_use = None
        if user_team_id and offer["offering_team_id"] == user_team_id:
            guidance_to_use = fa_guidance

        # Sign via FreeAgencyService (with budget stance modifier for user team)
        result = fa_service.sign_free_agent(
            player_id=offer["player_id"],
            team_id=offer["offering_team_id"],
            skip_preference_check=True,  # Already checked
            fa_guidance=guidance_to_use
        )

        if result.get("success"):
            # Update offer statuses
            offers_api.update_offer_status(offer["offer_id"], "accepted")

            # Reject other offers for this player
            all_offers = offers_api.get_offers_by_player(
                self._dynasty_id, offer["player_id"]
            )
            other_ids = [
                o["offer_id"] for o in all_offers
                if o["offer_id"] != offer["offer_id"]
                and o["status"] == "pending"
            ]
            if other_ids:
                offers_api.bulk_update_status(other_ids, "rejected")

            self._logger.info(
                f"Player {offer['player_id']} accepted offer from "
                f"Team {offer['offering_team_id']}: ${offer['aav']:,}/yr"
            )

            # Extract player data from contract_details for headline generation
            contract_details = result.get("contract_details", {})

            return {
                "player_id": offer["player_id"],
                "outcome": "signed",
                "team_id": offer["offering_team_id"],
                "aav": offer["aav"],
                "years": offer["years"],
                "player_name": result.get("player_name", ""),
                "position": contract_details.get("position", ""),
                "overall": contract_details.get("overall", 0),
                "age": contract_details.get("age", 0),
            }

        return {
            "player_id": offer["player_id"],
            "outcome": "signing_failed",
            "error": result.get("rejection_reason", "Unknown error")
        }

    # -------------------------------------------------------------------------
    # Summary Methods
    # -------------------------------------------------------------------------

    def get_wave_summary(self) -> Dict[str, Any]:
        """
        Get summary of current wave state for UI.

        Returns:
            Dict with wave info, pending offer counts, and available players
        """
        state = self.get_wave_state()
        offers_api = self._get_offers_api()

        pending_count = offers_api.get_pending_offers_count(self._dynasty_id)

        return {
            "wave": state["current_wave"],
            "wave_name": state["wave_name"],
            "current_day": state["current_day"],
            "days_in_wave": state["days_in_wave"],
            "days_remaining": state["days_in_wave"] - state["current_day"] + 1,
            "wave_complete": state["wave_complete"],
            "signing_allowed": state["signing_allowed"],
            "pending_offers": pending_count,
            "post_draft_available": state["post_draft_available"]
        }