"""
Trade Personality Modifiers

Applies GM personality traits to trade asset valuations and decision-making.
Translates abstract GM traits (0.0-1.0) into concrete value multipliers.
"""

from typing import Tuple, Optional
from dataclasses import dataclass

from team_management.gm_archetype import GMArchetype
from transactions.models import TradeAsset, AssetType, DraftPick


@dataclass
class TeamContext:
    """
    Team situation and context for trade evaluation.

    Used to apply situational modifiers based on team performance,
    needs, cap space, and other factors.
    """
    team_id: int
    season: int
    wins: int
    losses: int

    # Playoff positioning
    playoff_position: Optional[int] = None  # 1-7 in conference, None if out
    games_out_of_playoff: Optional[int] = None  # Games behind wildcard spot

    # Financial context
    cap_space: int = 0  # Available cap space in dollars
    cap_percentage: float = 0.0  # Percentage of cap available (0.0-1.0)

    # Team needs
    top_needs: list = None  # List of position strings (e.g., ['quarterback', 'edge_rusher'])

    # Situational flags
    is_deadline: bool = False  # Trade deadline scenario
    is_offseason: bool = False  # Offseason trading period

    def __post_init__(self):
        """Initialize default values"""
        if self.top_needs is None:
            self.top_needs = []

    @property
    def total_games(self) -> int:
        """Total games played"""
        return self.wins + self.losses

    @property
    def win_percentage(self) -> float:
        """Current win percentage (0.0-1.0)"""
        if self.total_games == 0:
            return 0.5  # Default for pre-season
        return self.wins / self.total_games

    @property
    def is_playoff_contender(self) -> bool:
        """Is team in playoff contention?"""
        if self.playoff_position:
            return True
        if self.games_out_of_playoff is not None:
            return self.games_out_of_playoff <= 2  # Within 2 games
        return self.win_percentage >= 0.500  # Above .500

    @property
    def is_rebuilding(self) -> bool:
        """Is team in rebuild mode?"""
        return self.win_percentage < 0.400


class PersonalityModifiers:
    """
    Applies GM personality trait modifiers to trade asset valuations.

    Each trait modifier method takes an asset, GM archetype, and team context,
    then returns a multiplier (typically 0.50x-2.00x) to adjust the asset's
    perceived value for that specific GM.

    Modifier Stacking Rules:
    - Individual modifiers capped at 0.50x-2.00x (50% reduction to 100% premium)
    - Combined modifiers capped at 0.50x-2.00x (after all traits applied)
    - Neutral trait value (0.5) produces 1.0x multiplier (no change)
    """

    # Multiplier caps
    MIN_MODIFIER = 0.50
    MAX_MODIFIER = 2.00

    @staticmethod
    def _cap_modifier(value: float) -> float:
        """Cap modifier to acceptable range"""
        return max(PersonalityModifiers.MIN_MODIFIER,
                   min(PersonalityModifiers.MAX_MODIFIER, value))

    # ============================================================================
    # CORE PERSONALITY TRAIT MODIFIERS
    # ============================================================================

    @classmethod
    def apply_risk_tolerance_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """
        Apply risk tolerance modifier to asset value.

        Risk-averse GMs (low trait):
        - Discount unproven young players (-20%)
        - Discount injured/suspension-risk players (-20%)
        - Prefer proven veterans (+10%)

        Risk-seeking GMs (high trait):
        - Premium on high-upside young players (+20%)
        - Willing to gamble on boom/bust prospects (+15%)

        Formula:
        - Base: 1.0x (neutral at 0.5 trait)
        - Young players (age < 25): 0.8x at trait=0.0, 1.2x at trait=1.0
        - Veterans (age >= 30): 1.1x at trait=0.0, 0.9x at trait=1.0

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values
            team_context: Current team situation

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if asset.asset_type != AssetType.PLAYER:
            return 1.0  # Risk tolerance doesn't affect picks

        if not asset.age:
            return 1.0  # Can't evaluate without age data

        # Young players (< 25): High risk/high reward
        if asset.age < 25:
            # 0.0 trait = 0.8x (discount), 1.0 trait = 1.2x (premium)
            multiplier = 0.8 + (gm.risk_tolerance * 0.4)
            return cls._cap_modifier(multiplier)

        # Veterans (>= 30): Low risk/proven production
        elif asset.age >= 30:
            # 0.0 trait = 1.1x (premium), 1.0 trait = 0.9x (discount)
            multiplier = 1.1 - (gm.risk_tolerance * 0.2)
            return cls._cap_modifier(multiplier)

        # Prime age (25-29): Neutral regardless of risk tolerance
        return 1.0

    @classmethod
    def apply_win_now_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """
        Apply win-now mentality modifier to asset value.

        Win-now GMs (high trait + playoff contender):
        - Major premium on proven players (+30-40%)
        - Discount draft picks (-20-30%)
        - Extra premium if player fills team need (+10%)

        Rebuilding GMs (low trait OR bad record):
        - Premium on draft picks (+20-40%)
        - Discount aging veterans (-20-30%)

        Formula:
        - Proven players (27-32, 85+ OVR):
          * Contender: 1.0 + (win_now * 0.4) = 1.0-1.4x
          * Rebuilding: 1.0 - (win_now * 0.3) = 0.7-1.0x
        - Draft picks:
          * Contender: 1.0 - (win_now * 0.3) = 0.7-1.0x
          * Rebuilding: 1.0 + ((1.0 - win_now) * 0.4) = 1.0-1.4x

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values
            team_context: Current team situation

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        # Determine team strategy context
        is_contender = team_context.is_playoff_contender
        is_rebuilding = team_context.is_rebuilding

        # Draft picks: Value based on team strategy
        if asset.asset_type == AssetType.DRAFT_PICK:
            if is_contender:
                # Contenders devalue picks (desperate for wins now)
                # High win_now = bigger discount
                multiplier = 1.0 - (gm.win_now_mentality * 0.3)
            elif is_rebuilding:
                # Rebuilders premium picks (building for future)
                # Low win_now = bigger premium
                multiplier = 1.0 + ((1.0 - gm.win_now_mentality) * 0.4)
            else:
                # Middle-of-pack: Slight bias based on win_now
                multiplier = 1.0 + ((0.5 - gm.win_now_mentality) * 0.2)

            return cls._cap_modifier(multiplier)

        # Players: Proven veterans vs young prospects
        if asset.asset_type == AssetType.PLAYER:
            # Proven veteran (prime age + high overall)
            is_proven = (asset.age and 27 <= asset.age <= 32 and
                        asset.overall_rating and asset.overall_rating >= 85)

            # Aging veteran (past prime)
            is_aging = asset.age and asset.age >= 33

            if is_proven and is_contender:
                # Proven player for contender = premium
                multiplier = 1.0 + (gm.win_now_mentality * 0.4)
                return cls._cap_modifier(multiplier)

            elif is_aging and is_rebuilding:
                # Old player for rebuilder = discount
                multiplier = 1.0 - (gm.win_now_mentality * 0.3)
                return cls._cap_modifier(multiplier)

        # Default: No strong modifier
        return 1.0

    @classmethod
    def apply_draft_pick_value_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype
    ) -> float:
        """
        Apply draft pick value philosophy modifier.

        High draft_pick_value GMs (0.7-1.0):
        - Value picks 20-50% more than baseline
        - "Draft hoarders" who love accumulating picks

        Low draft_pick_value GMs (0.0-0.3):
        - Value picks 20-30% less than baseline
        - "Win-now" traders who prefer proven talent

        Formula:
        - trait=0.0: 0.7x (major discount on picks)
        - trait=0.5: 1.0x (neutral)
        - trait=1.0: 1.5x (major premium on picks)

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if asset.asset_type != AssetType.DRAFT_PICK:
            return 1.0  # Only affects draft picks

        # Linear scaling: 0.0 trait = 0.7x, 0.5 trait = 1.0x, 1.0 trait = 1.5x
        multiplier = 0.7 + (gm.draft_pick_value * 0.8)
        return cls._cap_modifier(multiplier)

    @classmethod
    def apply_cap_management_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """
        Apply cap management philosophy modifier.

        Conservative GMs (high trait):
        - Discount expensive contracts (-20-40%)
        - Premium on cheap contracts (+10-20%)
        - Extra penalty if team has low cap space

        Aggressive GMs (low trait):
        - Less concerned about cap hits (neutral to slight premium)
        - Willing to take on bad contracts for value

        Formula:
        - Expensive contract (>$20M/year):
          * High cap_mgmt: 0.6-0.8x discount
          * Low cap_mgmt: 0.9-1.0x (minor discount)
        - Cheap contract (<$5M/year):
          * High cap_mgmt: 1.1-1.2x premium
          * Low cap_mgmt: 1.0x (neutral)

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values
            team_context: Current team situation

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if asset.asset_type != AssetType.PLAYER:
            return 1.0  # Only affects players with contracts

        if not asset.annual_cap_hit:
            return 1.0  # Can't evaluate without cap hit data

        cap_hit_millions = asset.annual_cap_hit / 1_000_000

        # Expensive contract (>$20M/year)
        if cap_hit_millions > 20:
            # High cap_management = bigger discount
            # 0.0 trait = 0.9x, 1.0 trait = 0.6x
            base_discount = 0.4  # Maximum 40% discount
            discount = base_discount * gm.cap_management
            multiplier = 1.0 - discount

            # Extra penalty if team has low cap space
            if team_context.cap_percentage < 0.1:  # Less than 10% cap available
                multiplier *= 0.9  # Additional 10% penalty

            return cls._cap_modifier(multiplier)

        # Cheap contract (<$5M/year) - value for conservative GMs
        elif cap_hit_millions < 5:
            # High cap_management = premium on cheap deals
            # 0.0 trait = 1.0x, 1.0 trait = 1.2x
            multiplier = 1.0 + (gm.cap_management * 0.2)
            return cls._cap_modifier(multiplier)

        # Mid-range contract ($5-20M): Minor modifier
        else:
            return 1.0

    @classmethod
    def apply_veteran_preference_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype
    ) -> float:
        """
        Apply veteran vs youth preference modifier.

        Veteran-focused GMs (high trait):
        - Premium on proven veterans (28-32 age) (+15-20%)
        - Discount on rookies/young players (-10-15%)

        Youth-focused GMs (low trait):
        - Premium on young players (21-24) (+15-20%)
        - Discount on aging veterans (33+) (-15-20%)

        Formula:
        - Veterans (28-32): 0.85x at trait=0.0, 1.2x at trait=1.0
        - Young (21-24): 1.2x at trait=0.0, 0.85x at trait=1.0
        - Aging (33+): 1.0x at trait=0.0, 0.8x at trait=1.0

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if asset.asset_type != AssetType.PLAYER:
            return 1.0  # Only affects players

        if not asset.age:
            return 1.0  # Can't evaluate without age

        # Young players (21-24)
        if 21 <= asset.age <= 24:
            # Low trait = premium, high trait = discount
            # 0.0 trait = 1.2x, 1.0 trait = 0.85x
            multiplier = 1.2 - (gm.veteran_preference * 0.35)
            return cls._cap_modifier(multiplier)

        # Prime veterans (28-32)
        elif 28 <= asset.age <= 32:
            # High trait = premium, low trait = discount
            # 0.0 trait = 0.85x, 1.0 trait = 1.2x
            multiplier = 0.85 + (gm.veteran_preference * 0.35)
            return cls._cap_modifier(multiplier)

        # Aging veterans (33+)
        elif asset.age >= 33:
            # High trait = neutral, low trait = discount
            # 0.0 trait = 1.0x, 1.0 trait = 0.8x
            multiplier = 1.0 - (gm.veteran_preference * 0.2)
            return cls._cap_modifier(multiplier)

        # Mid-career (25-27): Neutral
        return 1.0

    @classmethod
    def apply_star_chasing_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype
    ) -> float:
        """
        Apply star-chasing vs balanced roster modifier.

        Star-chasing GMs (high trait):
        - Major premium on elite players (90+ OVR) (+30-50%)
        - Discount on average starters (75-84 OVR) (-10%)

        Balanced GMs (low trait):
        - Neutral to slight discount on elite players
        - Premium on solid depth players (+10%)

        Formula:
        - Elite (90+ OVR): 1.0x at trait=0.0, 1.5x at trait=1.0
        - Stars (85-89 OVR): 1.0x at trait=0.0, 1.2x at trait=1.0
        - Average (75-84 OVR): 1.1x at trait=0.0, 0.9x at trait=1.0

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if asset.asset_type != AssetType.PLAYER:
            return 1.0  # Only affects players

        if not asset.overall_rating:
            return 1.0  # Can't evaluate without rating

        # Elite players (90+ OVR)
        if asset.overall_rating >= 90:
            # High trait = major premium
            # 0.0 trait = 1.0x, 1.0 trait = 1.5x
            multiplier = 1.0 + (gm.star_chasing * 0.5)
            return cls._cap_modifier(multiplier)

        # Star players (85-89 OVR)
        elif asset.overall_rating >= 85:
            # High trait = moderate premium
            # 0.0 trait = 1.0x, 1.0 trait = 1.2x
            multiplier = 1.0 + (gm.star_chasing * 0.2)
            return cls._cap_modifier(multiplier)

        # Average starters (75-84 OVR)
        elif asset.overall_rating >= 75:
            # Low trait = slight premium (values depth)
            # 0.0 trait = 1.1x, 1.0 trait = 0.9x
            multiplier = 1.1 - (gm.star_chasing * 0.2)
            return cls._cap_modifier(multiplier)

        # Below average (<75 OVR): Neutral
        return 1.0

    @classmethod
    def apply_loyalty_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype,
        is_acquiring: bool = True
    ) -> float:
        """
        Apply loyalty modifier (resistance to trading away existing players).

        This modifier primarily affects GIVING AWAY players, not acquiring them.
        High loyalty GMs are reluctant to trade away their own players.

        High loyalty GMs (high trait):
        - Major premium on keeping own players (+20-40%)
        - Makes them harder to trade away

        Low loyalty GMs (low trait):
        - Neutral to slight discount on own players
        - Willing to churn roster for upgrades

        Formula (when GIVING player):
        - 0.0 trait = 1.0x (neutral, willing to trade)
        - 1.0 trait = 1.4x (40% premium to keep player)

        Formula (when ACQUIRING player):
        - No modifier (loyalty doesn't affect incoming players)

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values
            is_acquiring: True if acquiring asset, False if giving away

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        # Loyalty only affects giving away players
        if is_acquiring or asset.asset_type != AssetType.PLAYER:
            return 1.0

        # High loyalty = premium on keeping own players
        # Makes trade less likely to happen
        # 0.0 trait = 1.0x, 1.0 trait = 1.4x
        multiplier = 1.0 + (gm.loyalty * 0.4)
        return cls._cap_modifier(multiplier)

    @classmethod
    def apply_premium_position_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype
    ) -> float:
        """
        Apply premium position focus modifier.

        Position-focused GMs (high trait):
        - Extra premium on QB/Edge/LT (+10-20%)
        - Neutral to slight discount on other positions

        Balanced GMs (low trait):
        - Equal value across all positions

        Formula:
        - Premium positions (QB/Edge/LT):
          * 0.0 trait = 1.0x, 1.0 trait = 1.2x
        - Other positions:
          * 0.0 trait = 1.0x, 1.0 trait = 0.95x (slight discount)

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if asset.asset_type != AssetType.PLAYER:
            return 1.0  # Only affects players

        if not asset.position:
            return 1.0  # Can't evaluate without position

        # Normalize position string
        position_lower = asset.position.lower()

        # Premium positions
        premium_positions = {'quarterback', 'qb', 'edge_rusher', 'edge',
                           'left_tackle', 'lt', 'offensive_tackle'}

        if position_lower in premium_positions:
            # High trait = premium
            # 0.0 trait = 1.0x, 1.0 trait = 1.2x
            multiplier = 1.0 + (gm.premium_position_focus * 0.2)
            return cls._cap_modifier(multiplier)
        else:
            # Slight discount on other positions when trait is high
            # 0.0 trait = 1.0x, 1.0 trait = 0.95x
            multiplier = 1.0 - (gm.premium_position_focus * 0.05)
            return cls._cap_modifier(multiplier)

    # ============================================================================
    # SITUATIONAL MODIFIERS
    # ============================================================================

    @classmethod
    def apply_desperation_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """
        Apply desperation modifier based on team performance.

        When team performance falls below GM's desperation_threshold,
        GMs become willing to overpay for proven help.

        Desperation triggers when:
        - Win % < desperation_threshold
        - Team was playoff contender but falling out
        - Trade deadline approaching with playoff hopes

        Formula:
        - Proven players: 1.0-1.3x premium when desperate
        - Draft picks: 0.8-1.0x discount when desperate
        - Severity based on how far below threshold

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values
            team_context: Current team situation

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        # Check if team is in desperation mode
        win_pct = team_context.win_percentage
        threshold = gm.desperation_threshold

        # Not desperate if performing above threshold
        if win_pct >= threshold:
            return 1.0

        # Calculate desperation severity (0.0-1.0)
        # Full desperation = 0.2 below threshold
        desperation_severity = min(1.0, (threshold - win_pct) / 0.2)

        # Draft picks: Discount when desperate (need wins now)
        if asset.asset_type == AssetType.DRAFT_PICK:
            # 0.0 severity = 1.0x, 1.0 severity = 0.8x
            multiplier = 1.0 - (desperation_severity * 0.2)
            return cls._cap_modifier(multiplier)

        # Proven players: Premium when desperate
        if asset.asset_type == AssetType.PLAYER:
            is_proven = (asset.age and 25 <= asset.age <= 32 and
                        asset.overall_rating and asset.overall_rating >= 80)

            if is_proven:
                # 0.0 severity = 1.0x, 1.0 severity = 1.3x
                multiplier = 1.0 + (desperation_severity * 0.3)
                return cls._cap_modifier(multiplier)

        return 1.0

    @classmethod
    def apply_deadline_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """
        Apply trade deadline urgency modifier.

        At trade deadline, GMs with high deadline_activity become
        more aggressive in their valuations.

        Formula:
        - Proven players (if contending):
          * 1.0x at trait=0.0, 1.2x at trait=1.0
        - Draft picks (if contending):
          * 1.0x at trait=0.0, 0.85x at trait=1.0

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values
            team_context: Current team situation

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if not team_context.is_deadline:
            return 1.0  # Not at deadline

        if not team_context.is_playoff_contender:
            return 1.0  # Only affects contenders at deadline

        # Draft picks: Contenders discount picks at deadline
        if asset.asset_type == AssetType.DRAFT_PICK:
            # High deadline_activity = bigger discount
            # 0.0 trait = 1.0x, 1.0 trait = 0.85x
            multiplier = 1.0 - (gm.deadline_activity * 0.15)
            return cls._cap_modifier(multiplier)

        # Proven players: Contenders premium at deadline
        if asset.asset_type == AssetType.PLAYER:
            is_proven = (asset.age and 25 <= asset.age <= 32 and
                        asset.overall_rating and asset.overall_rating >= 80)

            if is_proven:
                # High deadline_activity = bigger premium
                # 0.0 trait = 1.0x, 1.0 trait = 1.2x
                multiplier = 1.0 + (gm.deadline_activity * 0.2)
                return cls._cap_modifier(multiplier)

        return 1.0

    @classmethod
    def apply_team_need_modifier(
        cls,
        asset: TradeAsset,
        team_context: TeamContext
    ) -> float:
        """
        Apply team need modifier (not GM trait-based).

        When asset fills a top-3 team need, apply premium.
        This is situation-based, not personality-based.

        Formula:
        - Top need (#1): 1.3x premium
        - Secondary need (#2-3): 1.15x premium
        - Not a need: 1.0x (neutral)

        Args:
            asset: The trade asset being evaluated
            team_context: Current team situation

        Returns:
            Value multiplier (0.50x-2.00x)
        """
        if asset.asset_type != AssetType.PLAYER:
            return 1.0  # Only affects players

        if not asset.position or not team_context.top_needs:
            return 1.0  # Can't evaluate without position/needs data

        # Normalize position
        position_lower = asset.position.lower()

        # Check if position fills a need
        if position_lower in team_context.top_needs[:1]:
            # Top need
            return cls._cap_modifier(1.3)
        elif position_lower in team_context.top_needs[:3]:
            # Secondary need
            return cls._cap_modifier(1.15)

        return 1.0

    # ============================================================================
    # COMBINED MODIFIERS
    # ============================================================================

    @classmethod
    def calculate_total_modifier(
        cls,
        asset: TradeAsset,
        gm: GMArchetype,
        team_context: TeamContext,
        is_acquiring: bool = True
    ) -> float:
        """
        Calculate total modifier by combining all applicable trait modifiers.

        Combines all personality and situational modifiers, then caps
        the final result to 0.50x-2.00x range.

        Args:
            asset: The trade asset being evaluated
            gm: GM archetype with trait values
            team_context: Current team situation
            is_acquiring: True if acquiring asset, False if giving away

        Returns:
            Combined value multiplier (0.50x-2.00x)
        """
        # Start with neutral multiplier
        total = 1.0

        # Apply core personality traits
        total *= cls.apply_risk_tolerance_modifier(asset, gm, team_context)
        total *= cls.apply_win_now_modifier(asset, gm, team_context)
        total *= cls.apply_draft_pick_value_modifier(asset, gm)
        total *= cls.apply_cap_management_modifier(asset, gm, team_context)
        total *= cls.apply_veteran_preference_modifier(asset, gm)
        total *= cls.apply_star_chasing_modifier(asset, gm)
        total *= cls.apply_loyalty_modifier(asset, gm, is_acquiring)
        total *= cls.apply_premium_position_modifier(asset, gm)

        # Apply situational modifiers
        total *= cls.apply_desperation_modifier(asset, gm, team_context)
        total *= cls.apply_deadline_modifier(asset, gm, team_context)
        total *= cls.apply_team_need_modifier(asset, team_context)

        # Cap final result
        return cls._cap_modifier(total)

    @classmethod
    def calculate_acceptance_threshold(
        cls,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> Tuple[float, float]:
        """
        Calculate acceptable value ratio range for this GM.

        Returns (min_ratio, max_ratio) where:
        - min_ratio < actual_ratio < max_ratio = ACCEPT
        - Ratio close to bounds = COUNTER
        - Ratio outside bounds = REJECT

        Base thresholds (0.80-1.20) adjusted by:
        - trade_frequency: Higher = wider acceptable range
        - risk_tolerance: Higher = wider acceptable range
        - desperation: Narrower range (more willing to overpay)

        Formula:
        - Base: 0.80-1.20 (±20% fair value)
        - Adjusted by trade_frequency: ±15% to ±30%
        - Adjusted by risk_tolerance: ±10% to ±25%
        - Desperation: Tighten losing side, expand winning side

        Args:
            gm: GM archetype with trait values
            team_context: Current team situation

        Returns:
            Tuple of (min_acceptable_ratio, max_acceptable_ratio)
        """
        # Base thresholds
        base_min = 0.80
        base_max = 1.20

        # Adjust by trade_frequency (more active = wider range)
        # 0.0 trait = ±15%, 1.0 trait = ±30%
        frequency_width = 0.15 + (gm.trade_frequency * 0.15)

        # Adjust by risk_tolerance (higher risk = wider range)
        # 0.0 trait = ±10%, 1.0 trait = ±25%
        risk_width = 0.10 + (gm.risk_tolerance * 0.15)

        # Combined width adjustment (average of both)
        width_adjustment = (frequency_width + risk_width) / 2

        # Calculate adjusted thresholds
        min_ratio = 1.0 - width_adjustment
        max_ratio = 1.0 + width_adjustment

        # Apply desperation adjustment (if applicable)
        if team_context.win_percentage < gm.desperation_threshold:
            desperation_severity = min(1.0,
                (gm.desperation_threshold - team_context.win_percentage) / 0.2)

            # Desperate teams willing to overpay (expand max, tighten min)
            min_ratio *= (1.0 - desperation_severity * 0.05)  # Slight tightening
            max_ratio *= (1.0 + desperation_severity * 0.15)  # Significant expansion

        # Ensure reasonable bounds (minimum ±10%, maximum ±40%)
        min_ratio = max(0.60, min(0.90, min_ratio))
        max_ratio = min(1.40, max(1.10, max_ratio))

        return (min_ratio, max_ratio)
