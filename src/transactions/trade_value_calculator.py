"""
Trade Value Calculator

Calculates objective trade values for NFL players and draft picks.
Evaluates trade fairness and provides recommendations.
"""

from typing import Dict, List, Optional
from datetime import date

from .models import TradeAsset, DraftPick, TradeProposal, AssetType, FairnessRating
from .transaction_constants import (
    PositionValueTiers,
    AgeCurveParameters,
    TradeValueScaling
)


class TradeValueCalculator:
    """
    Calculates objective trade values for NFL players and draft picks.

    Value Units:
    - 100 = Average NFL starter (75-80 overall)
    - 200 = Good starter (80-85 overall)
    - 300 = Pro Bowl level (85-90 overall)
    - 400+ = Elite/All-Pro (90+ overall)

    Values are in same units for players and picks to enable direct comparison.
    """

    def __init__(
        self,
        current_year: int = 2025,
        dynasty_id: str = "default_dynasty",
        player_roster_api=None,
        team_needs_analyzer=None
    ):
        """
        Initialize calculator with optional database access.

        Args:
            current_year: Current season year for future pick discounting
            dynasty_id: Dynasty identifier for dynasty isolation
            player_roster_api: PlayerRosterAPI for player data lookups
            team_needs_analyzer: For context-aware valuations
        """
        self.current_year = current_year
        self.dynasty_id = dynasty_id
        self.player_api = player_roster_api
        self.needs_analyzer = team_needs_analyzer

        # Position value tiers (multipliers) - Calibrated v1.1 (PRODUCTION)
        # Using PositionValueTiers constants from transaction_constants.py
        self.position_tiers = {
            # Tier 1: Premium positions
            'quarterback': PositionValueTiers.QUARTERBACK, 'qb': PositionValueTiers.QUARTERBACK,
            'edge_rusher': PositionValueTiers.EDGE_RUSHER, 'defensive_end': PositionValueTiers.EDGE_RUSHER, 'de': PositionValueTiers.EDGE_RUSHER,
            'left_tackle': PositionValueTiers.LEFT_TACKLE, 'lt': PositionValueTiers.LEFT_TACKLE,
            'right_tackle': PositionValueTiers.RIGHT_TACKLE, 'rt': PositionValueTiers.RIGHT_TACKLE,

            # Tier 2: High value positions
            'wide_receiver': PositionValueTiers.WIDE_RECEIVER, 'wr': PositionValueTiers.WIDE_RECEIVER,
            'cornerback': PositionValueTiers.CORNERBACK, 'cb': PositionValueTiers.CORNERBACK,
            'center': PositionValueTiers.CENTER, 'c': PositionValueTiers.CENTER,

            # Tier 3: Standard value positions
            'running_back': PositionValueTiers.RUNNING_BACK, 'rb': PositionValueTiers.RUNNING_BACK, 'fullback': PositionValueTiers.FULLBACK, 'fb': PositionValueTiers.FULLBACK,
            'tight_end': PositionValueTiers.TIGHT_END, 'te': PositionValueTiers.TIGHT_END,
            'linebacker': PositionValueTiers.LINEBACKER, 'lb': PositionValueTiers.LINEBACKER, 'mike': PositionValueTiers.LINEBACKER, 'sam': PositionValueTiers.LINEBACKER, 'will': PositionValueTiers.LINEBACKER,
            'safety': PositionValueTiers.SAFETY, 'ss': PositionValueTiers.SAFETY, 'fs': PositionValueTiers.SAFETY,
            'left_guard': PositionValueTiers.GUARD, 'lg': PositionValueTiers.GUARD,
            'right_guard': PositionValueTiers.GUARD, 'rg': PositionValueTiers.GUARD,

            # Tier 4: Lower value positions
            'defensive_tackle': PositionValueTiers.DEFENSIVE_TACKLE, 'dt': PositionValueTiers.DEFENSIVE_TACKLE,
            'nose_tackle': PositionValueTiers.NOSE_TACKLE, 'nt': PositionValueTiers.NOSE_TACKLE,
            'kicker': PositionValueTiers.KICKER, 'k': PositionValueTiers.KICKER,
            'punter': PositionValueTiers.PUNTER, 'p': PositionValueTiers.PUNTER,
        }

        # Age curves (peak years get 1.0x, decline after) - Calibrated v1.1
        # Using AgeCurveParameters constants from transaction_constants.py
        self.age_curves = {
            'quarterback': AgeCurveParameters.QUARTERBACK,
            'running_back': AgeCurveParameters.RUNNING_BACK,
            'wide_receiver': AgeCurveParameters.WIDE_RECEIVER,
            'tight_end': AgeCurveParameters.TIGHT_END,
            'offensive_line': AgeCurveParameters.OFFENSIVE_LINE,
            'defensive_line': AgeCurveParameters.DEFENSIVE_LINE,
            'linebacker': AgeCurveParameters.LINEBACKER,
            'defensive_back': AgeCurveParameters.DEFENSIVE_BACK,
        }

        # Jimmy Johnson Draft Pick Value Chart
        self.draft_pick_values: Dict[int, float] = {}
        self._init_draft_pick_chart()

    def _init_draft_pick_chart(self):
        """Initialize Jimmy Johnson draft pick value chart"""
        # Generate values for all 262 picks (7 rounds × 32 teams + comp picks)
        for overall_pick in range(1, 263):
            self.draft_pick_values[overall_pick] = self._jimmy_johnson_formula(overall_pick)

    def _jimmy_johnson_formula(self, overall_pick: int) -> float:
        """
        Calculate draft pick value using Jimmy Johnson chart formula.

        Original chart had pick #1 = 3000 points, exponential decay.
        We scale to match player values (100 = average starter).

        Args:
            overall_pick: Overall pick number (1-262)

        Returns:
            Trade value in same units as players
        """
        if overall_pick == 1:
            base_value = 3000.0
        elif overall_pick <= 32:  # 1st round
            # Linear interpolation from 3000 to 600
            base_value = 3000 - (overall_pick - 1) * (2400 / 31)
        elif overall_pick <= 64:  # 2nd round
            # Linear interpolation from 600 to 270
            base_value = 600 - (overall_pick - 32) * (330 / 32)
        elif overall_pick <= 96:  # 3rd round
            # Linear interpolation from 270 to 148
            base_value = 270 - (overall_pick - 64) * (122 / 32)
        elif overall_pick <= 128:  # 4th round
            base_value = 148 - (overall_pick - 96) * (73 / 32)
        elif overall_pick <= 160:  # 5th round
            base_value = 75 - (overall_pick - 128) * (35 / 32)
        elif overall_pick <= 192:  # 6th round
            base_value = 40 - (overall_pick - 160) * (20 / 32)
        else:  # 7th round and comp picks
            # Exponential decay for late picks
            base_value = 20 * (0.95 ** (overall_pick - 192))

        # Scale to player value units (100 = starter)
        # Top pick (~3000) should equal elite young QB (~600 value)
        # Mid-1st (~1000) should equal good starter (~200 value)
        scaled_value = base_value / TradeValueScaling.DRAFT_PICK_SCALING_FACTOR

        return scaled_value

    def calculate_player_value(
        self,
        player_id: Optional[int] = None,
        overall_rating: Optional[int] = None,
        position: Optional[str] = None,
        age: Optional[int] = None,
        contract_years_remaining: Optional[int] = None,
        annual_cap_hit: Optional[int] = None,
        acquiring_team_id: Optional[int] = None,
    ) -> float:
        """
        Calculate trade value for an NFL player.

        Value Formula:
        base_value = (overall_rating - 50) ^ 1.8 × position_tier × age_multiplier
        contract_adjustment = f(years_remaining, cap_hit, guarantees)
        need_multiplier = 0.7-1.3 based on acquiring team's positional need

        final_value = base_value × contract_adjustment × need_multiplier

        Args:
            player_id: Player ID for database lookup (if available)
            overall_rating: Player overall rating (0-100)
            position: Player position
            age: Player age
            contract_years_remaining: Years left on contract
            annual_cap_hit: Average annual cap hit
            acquiring_team_id: Team acquiring player (for need context)

        Returns:
            Trade value in arbitrary units (100 = average starter)
        """
        # If player_id provided, fetch data from database
        if player_id and self.player_api:
            player_data = self.player_api.get_player_by_id(self.dynasty_id, player_id)
            if not player_data:
                # Player not found - skip auto-population and use provided params
                pass
            else:
                # Parse attributes if stored as JSON string
                attributes = player_data['attributes']
                if isinstance(attributes, str):
                    import json
                    attributes = json.loads(attributes)

                # Parse positions if stored as JSON string
                positions = player_data['positions']
                if isinstance(positions, str):
                    import json
                    positions = json.loads(positions)

                overall_rating = attributes['overall']
                position = positions[0] if positions else 'unknown'
                # Calculate age from birthdate
                birthdate = date.fromisoformat(player_data['birthdate'])
                age = (date.today() - birthdate).days // 365
                # Note: Contract data fetching removed - caller provides contract params

        # Validate inputs
        if not all([overall_rating is not None, position, age is not None]):
            raise ValueError("Must provide overall_rating, position, and age")

        # Step 1: Base value from overall rating
        # Use power curve: 50 OVR = 0, 75 OVR = 100, 85 OVR = 300, 95 OVR = 700
        if overall_rating <= TradeValueScaling.BASE_VALUE_OFFSET:
            base_value = 0.0
        else:
            base_value = ((overall_rating - TradeValueScaling.BASE_VALUE_OFFSET) ** TradeValueScaling.BASE_VALUE_EXPONENT) / TradeValueScaling.BASE_VALUE_DIVISOR
        base_value = max(0, base_value)  # No negative values

        # Step 2: Position tier multiplier
        position_multiplier = self._get_position_multiplier(position)

        # Step 3: Age curve multiplier
        age_multiplier = self._get_age_multiplier(position, age)

        # Step 4: Contract adjustment
        contract_multiplier = self._get_contract_multiplier(
            contract_years_remaining, annual_cap_hit, overall_rating
        )

        # Step 5: Team need multiplier (if applicable)
        need_multiplier = 1.0
        if acquiring_team_id and self.needs_analyzer:
            need_multiplier = self._get_need_multiplier(acquiring_team_id, position)

        # Calculate final value
        final_value = (
            base_value
            * position_multiplier
            * age_multiplier
            * contract_multiplier
            * need_multiplier
        )

        return round(final_value, 1)

    def _get_position_multiplier(self, position: str) -> float:
        """Get position value tier multiplier"""
        # Normalize position string
        position_normalized = position.lower().replace(' ', '_')
        return self.position_tiers.get(position_normalized, 1.0)

    def _get_age_multiplier(self, position: str, age: int) -> float:
        """
        Calculate age curve multiplier.

        Returns 1.0 during peak years, declines before/after.
        """
        # Determine position group for age curve
        position_group = self._get_position_group(position)
        curve = self.age_curves.get(position_group, {
            'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12
        })

        peak_start = curve['peak_start']
        peak_end = curve['peak_end']
        decline_rate = curve['decline_rate']

        if peak_start <= age <= peak_end:
            # Peak years
            return 1.0
        elif age < peak_start:
            # Pre-peak (slight discount for inexperience)
            years_before_peak = peak_start - age
            return max(0.80, 1.0 - (years_before_peak * 0.05))
        else:
            # Post-peak decline
            years_after_peak = age - peak_end
            return max(0.40, 1.0 - (years_after_peak * decline_rate))

    def _get_position_group(self, position: str) -> str:
        """Map specific position to age curve group"""
        position = position.lower()
        if 'quarterback' in position or 'qb' in position:
            return 'quarterback'
        elif 'running' in position or 'rb' in position or 'fullback' in position:
            return 'running_back'
        elif 'receiver' in position or 'wr' in position:
            return 'wide_receiver'
        elif 'tight' in position or 'te' in position:
            return 'tight_end'
        elif any(ol in position for ol in ['tackle', 'guard', 'center', 'offensive_line']):
            return 'offensive_line'
        elif any(dl in position for dl in ['defensive_end', 'defensive_tackle', 'nose_tackle', 'edge']):
            return 'defensive_line'
        elif 'linebacker' in position or 'lb' in position:
            return 'linebacker'
        else:
            return 'defensive_back'

    def _get_contract_multiplier(
        self,
        years_remaining: Optional[int],
        annual_cap_hit: Optional[int],
        overall_rating: int
    ) -> float:
        """
        Calculate contract value adjustment.

        Good contracts increase value, bad contracts decrease it.
        """
        if not years_remaining or not annual_cap_hit:
            # No contract data = assume reasonable contract
            return 1.0

        # Calculate "fair" annual value based on overall rating
        # 85 OVR = ~$15M, 90 OVR = ~$25M, 95 OVR = ~$40M
        if overall_rating >= 90:
            fair_value = 15_000_000 + (overall_rating - 90) * 5_000_000
        elif overall_rating >= 80:
            fair_value = 5_000_000 + (overall_rating - 80) * 1_000_000
        else:
            fair_value = (overall_rating - 50) * 100_000

        # Calculate value/cost ratio
        value_ratio = fair_value / annual_cap_hit if annual_cap_hit > 0 else 1.0

        # Contract length adjustment
        if years_remaining == 1:
            # Expiring contract = lower value (rental)
            length_mult = 0.85
        elif years_remaining <= 3:
            # Good length
            length_mult = 1.0
        elif years_remaining <= 5:
            # Longer term commitment
            length_mult = 0.95
        else:
            # Very long contract = albatross risk
            length_mult = 0.85

        # Combine value ratio and length
        if value_ratio >= 1.5:
            # Great contract (underpaid)
            contract_mult = 1.20
        elif value_ratio >= 1.2:
            # Good contract
            contract_mult = 1.10
        elif value_ratio >= 0.8:
            # Fair contract
            contract_mult = 1.0
        elif value_ratio >= 0.6:
            # Slightly overpaid
            contract_mult = 0.90
        else:
            # Bad contract (very overpaid)
            contract_mult = 0.70

        return contract_mult * length_mult

    def _get_need_multiplier(self, team_id: int, position: str) -> float:
        """
        Adjust value based on acquiring team's positional need.

        Returns:
            0.7 = No need (have elite starter)
            1.0 = Moderate need
            1.3 = Critical need (have no starter)
        """
        if not self.needs_analyzer:
            return 1.0

        team_needs = self.needs_analyzer.analyze_team_needs(team_id)

        # Find need for this position
        for need in team_needs:
            if need['position'].lower() == position.lower():
                urgency = need['urgency_score']  # 1-5
                if urgency >= 5:
                    return 1.3  # Critical need
                elif urgency >= 4:
                    return 1.15  # High need
                elif urgency >= 3:
                    return 1.0  # Medium need
                elif urgency >= 2:
                    return 0.9  # Low need
                else:
                    return 0.7  # No need

        return 1.0  # Default if position not found

    def calculate_pick_value(
        self,
        draft_pick: DraftPick,
        team_wins: Optional[int] = None,
        team_losses: Optional[int] = None,
    ) -> float:
        """
        Calculate trade value for a draft pick.

        Args:
            draft_pick: DraftPick object
            team_wins: Current wins (for projection)
            team_losses: Current losses (for projection)

        Returns:
            Trade value in same units as players
        """
        # Estimate overall pick number if not provided
        if not draft_pick.overall_pick_projected:
            if team_wins is not None and team_losses is not None:
                draft_pick.estimate_overall_pick(team_wins, team_losses)
            else:
                # Use middle of round as default
                draft_pick.overall_pick_projected = (draft_pick.round - 1) * 32 + 16

        overall_pick = draft_pick.overall_pick_projected

        # Get base value from Jimmy Johnson chart
        base_value = self.draft_pick_values.get(overall_pick, 1.0)

        # Future year discount (5% per year)
        years_out = draft_pick.year - self.current_year
        if years_out > 0:
            discount = 0.95 ** years_out
            base_value *= discount

        # Uncertainty adjustment for projections
        if draft_pick.projected_range_max and draft_pick.projected_range_min:
            uncertainty = draft_pick.projected_range_max - draft_pick.projected_range_min
            if uncertainty > 15:  # High uncertainty
                base_value *= 0.90  # 10% discount
            elif uncertainty > 8:
                base_value *= 0.95  # 5% discount

        return round(base_value, 1)

    def evaluate_trade(
        self,
        team1_id: int,
        team1_assets: List[TradeAsset],
        team2_id: int,
        team2_assets: List[TradeAsset],
    ) -> TradeProposal:
        """
        Evaluate complete trade proposal for fairness.

        Args:
            team1_id: Team ID proposing trade
            team1_assets: Assets team1 is giving up
            team2_id: Team ID receiving proposal
            team2_assets: Assets team2 is giving up

        Returns:
            TradeProposal with fairness evaluation
        """
        # Calculate total values
        team1_total = sum(asset.trade_value for asset in team1_assets)
        team2_total = sum(asset.trade_value for asset in team2_assets)

        # Calculate value ratio (what team2 gives / what team1 gives)
        # Ratio > 1.0 means team1 is getting more value
        # Ratio < 1.0 means team2 is getting more value
        if team1_total == 0:
            value_ratio = float('inf') if team2_total > 0 else 1.0
        else:
            value_ratio = team2_total / team1_total

        # Determine fairness
        fairness = TradeProposal.calculate_fairness(value_ratio)

        # Create proposal
        proposal = TradeProposal(
            team1_id=team1_id,
            team1_assets=team1_assets,
            team1_total_value=team1_total,
            team2_id=team2_id,
            team2_assets=team2_assets,
            team2_total_value=team2_total,
            value_ratio=value_ratio,
            fairness_rating=fairness,
            initiating_team_id=team1_id
        )

        return proposal
