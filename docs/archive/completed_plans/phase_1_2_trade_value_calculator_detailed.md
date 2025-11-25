# Phase 1.2: Trade Value Calculator - Detailed Implementation Plan

## Overview

Build a comprehensive trade valuation system that calculates objective values for both players and draft picks, evaluates trade fairness, and benchmarks against real-world NFL trades. This system will be the foundation for AI-driven trade proposals in Phase 1.3.

---

## File Structure

```
src/transactions/
├── trade_value_calculator.py    # Core calculator class
└── models.py                     # Data models (TradeAsset, DraftPick, TradeProposal)

tests/transactions/
├── test_trade_value_calculator.py  # 30+ comprehensive tests
└── test_trade_models.py            # Model validation tests

demo/trade_value_demo/
├── trade_value_demo.py            # Interactive demo with 5 scenarios
├── real_world_trades.json         # 10 historical NFL trades
└── benchmark_trades.py            # Benchmarking script

docs/
└── trade_value_formulas.md        # Mathematical documentation
```

---

## Step 1: Data Models

**File**: `src/transactions/models.py`

### 1.1 DraftPick Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class DraftPick:
    """Represents a tradeable NFL draft pick"""

    round: int  # 1-7
    year: int   # Draft year (current or future)
    original_team_id: int  # Team that originally owned this pick
    current_team_id: int   # Team that currently owns it

    # For value calculation
    overall_pick_projected: Optional[int] = None  # 1-262 based on standings
    projected_range_min: Optional[int] = None     # Uncertainty range
    projected_range_max: Optional[int] = None

    # Metadata
    is_compensatory: bool = False
    is_conditional: bool = False  # Future enhancement

    def __post_init__(self):
        """Validate pick data"""
        if not 1 <= self.round <= 7:
            raise ValueError(f"Round must be 1-7, got {self.round}")

        if self.overall_pick_projected:
            if not 1 <= self.overall_pick_projected <= 262:
                raise ValueError(f"Overall pick must be 1-262, got {self.overall_pick_projected}")

    def estimate_overall_pick(self, team_wins: int, team_losses: int) -> int:
        """
        Estimate overall pick number based on team record.

        Args:
            team_wins: Current wins
            team_losses: Current losses

        Returns:
            Estimated overall pick number (1-262)
        """
        # Calculate draft position within round based on record
        # Worst record = pick 1, best record = pick 32
        win_percentage = team_wins / (team_wins + team_losses) if (team_wins + team_losses) > 0 else 0.5

        # Position in round (1-32, worst team = 1)
        position_in_round = int((1 - win_percentage) * 31) + 1
        position_in_round = max(1, min(32, position_in_round))

        # Calculate overall pick
        overall = (self.round - 1) * 32 + position_in_round

        self.overall_pick_projected = overall
        # Set uncertainty range (±3 picks for current year, ±10 for future)
        years_out = self.year - 2025  # Assuming 2025 is current
        uncertainty = 3 if years_out == 0 else 10
        self.projected_range_min = max(1, overall - uncertainty)
        self.projected_range_max = min(262, overall + uncertainty)

        return overall
```

### 1.2 TradeAsset Model

```python
from enum import Enum
from typing import Optional, Union

class AssetType(Enum):
    PLAYER = "PLAYER"
    DRAFT_PICK = "DRAFT_PICK"

@dataclass
class TradeAsset:
    """Union type for players or draft picks in trades"""

    asset_type: AssetType

    # Player data (populated if asset_type == PLAYER)
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    overall_rating: Optional[int] = None
    age: Optional[int] = None
    years_pro: Optional[int] = None
    contract_years_remaining: Optional[int] = None
    annual_cap_hit: Optional[int] = None
    total_remaining_guaranteed: Optional[int] = None

    # Pick data (populated if asset_type == DRAFT_PICK)
    draft_pick: Optional[DraftPick] = None

    # Calculated trade value (in arbitrary units)
    trade_value: float = 0.0

    # Context for valuation
    acquiring_team_id: Optional[int] = None  # Team receiving this asset

    def __post_init__(self):
        """Validate asset data"""
        if self.asset_type == AssetType.PLAYER:
            if not self.player_id:
                raise ValueError("Player assets must have player_id")
        elif self.asset_type == AssetType.DRAFT_PICK:
            if not self.draft_pick:
                raise ValueError("Draft pick assets must have draft_pick")

    def __str__(self) -> str:
        """Human-readable representation"""
        if self.asset_type == AssetType.PLAYER:
            return f"{self.player_name} ({self.position}, {self.overall_rating} OVR, Age {self.age})"
        else:
            return f"{self.draft_pick.year} Round {self.draft_pick.round} Pick"
```

### 1.3 TradeProposal Model

```python
from typing import List

class FairnessRating(Enum):
    VERY_FAIR = "VERY_FAIR"              # 0.95-1.05
    FAIR = "FAIR"                        # 0.80-0.95 or 1.05-1.20
    SLIGHTLY_UNFAIR = "SLIGHTLY_UNFAIR"  # 0.70-0.80 or 1.20-1.30
    VERY_UNFAIR = "VERY_UNFAIR"          # <0.70 or >1.30

@dataclass
class TradeProposal:
    """Complete trade package with valuation and validation"""

    # Team 1 (proposing team)
    team1_id: int
    team1_assets: List[TradeAsset]
    team1_total_value: float

    # Team 2 (receiving proposal)
    team2_id: int
    team2_assets: List[TradeAsset]
    team2_total_value: float

    # Fairness evaluation
    value_ratio: float  # team2_total / team1_total (1.0 = perfectly fair)
    fairness_rating: FairnessRating

    # Validation flags
    passes_cap_validation: bool = False
    passes_roster_validation: bool = False

    # Cap space after trade
    team1_cap_space_after: Optional[int] = None
    team2_cap_space_after: Optional[int] = None

    # Metadata
    proposed_date: Optional[str] = None
    initiating_team_id: Optional[int] = None

    @classmethod
    def calculate_fairness(cls, ratio: float) -> FairnessRating:
        """Determine fairness rating from value ratio"""
        if 0.95 <= ratio <= 1.05:
            return FairnessRating.VERY_FAIR
        elif 0.80 <= ratio <= 1.20:
            return FairnessRating.FAIR
        elif 0.70 <= ratio <= 1.30:
            return FairnessRating.SLIGHTLY_UNFAIR
        else:
            return FairnessRating.VERY_UNFAIR

    def is_acceptable(self) -> bool:
        """Check if trade is acceptable (fair enough to execute)"""
        return self.fairness_rating in [FairnessRating.VERY_FAIR, FairnessRating.FAIR]

    def get_summary(self) -> str:
        """Get human-readable trade summary"""
        team1_assets_str = ", ".join(str(a) for a in self.team1_assets)
        team2_assets_str = ", ".join(str(a) for a in self.team2_assets)

        return (
            f"TRADE PROPOSAL:\n"
            f"Team {self.team1_id} sends: {team1_assets_str} (Value: {self.team1_total_value:.1f})\n"
            f"Team {self.team2_id} sends: {team2_assets_str} (Value: {self.team2_total_value:.1f})\n"
            f"Value Ratio: {self.value_ratio:.3f} ({self.fairness_rating.value})\n"
            f"Acceptable: {self.is_acceptable()}"
        )
```

---

## Step 2: Trade Value Calculator Core

**File**: `src/transactions/trade_value_calculator.py`

### 2.1 Calculator Class Structure

```python
from typing import Dict, List, Optional, Tuple
from datetime import date
from .models import TradeAsset, DraftPick, TradeProposal, AssetType

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

    def __init__(self, current_year: int = 2025, database_api=None, team_needs_analyzer=None):
        """
        Initialize calculator with optional database access.

        Args:
            current_year: Current season year for future pick discounting
            database_api: Database API for player/contract lookups
            team_needs_analyzer: For context-aware valuations
        """
        self.current_year = current_year
        self.db = database_api
        self.needs_analyzer = team_needs_analyzer

        # Position value tiers (multipliers)
        self.position_tiers = {
            # Tier 1: Premium positions (2.0x)
            'quarterback': 2.0,
            'edge_rusher': 2.0, 'defensive_end': 2.0,
            'left_tackle': 2.0, 'right_tackle': 2.0,

            # Tier 2: High value (1.5x)
            'wide_receiver': 1.5, 'cornerback': 1.5,
            'center': 1.5,

            # Tier 3: Standard (1.0-1.3x)
            'running_back': 1.2, 'tight_end': 1.0,
            'linebacker': 1.2, 'safety': 1.1,
            'left_guard': 1.0, 'right_guard': 1.0,

            # Tier 4: Lower value (0.8-1.0x)
            'defensive_tackle': 0.9, 'nose_tackle': 0.8,
            'kicker': 0.8, 'punter': 0.8,
        }

        # Age curves (peak years get 1.0x, decline after)
        self.age_curves = {
            'quarterback': {'peak_start': 27, 'peak_end': 32, 'decline_rate': 0.10},
            'running_back': {'peak_start': 23, 'peak_end': 27, 'decline_rate': 0.15},
            'wide_receiver': {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12},
            'tight_end': {'peak_start': 26, 'peak_end': 30, 'decline_rate': 0.10},
            'offensive_line': {'peak_start': 26, 'peak_end': 31, 'decline_rate': 0.08},
            'defensive_line': {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12},
            'linebacker': {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.12},
            'defensive_back': {'peak_start': 25, 'peak_end': 29, 'decline_rate': 0.13},
        }

        # Jimmy Johnson Draft Pick Value Chart
        self._init_draft_pick_chart()

    def _init_draft_pick_chart(self):
        """Initialize Jimmy Johnson draft pick value chart"""
        # Empirically derived from historical NFL trades
        self.draft_pick_values = {}

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
        scaled_value = base_value / 15.0  # Empirical scaling factor

        return scaled_value
```

### 2.2 Player Valuation Method

```python
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
    if player_id and self.db:
        player_data = self.db.get_player(player_id)
        overall_rating = player_data['attributes']['overall']
        position = player_data['positions'][0]
        # Calculate age from birthdate
        birthdate = date.fromisoformat(player_data['birthdate'])
        age = (date.today() - birthdate).days // 365
        # Get contract data
        contract = self.db.get_player_contract(player_id)
        if contract:
            contract_years_remaining = contract['end_year'] - self.current_year + 1
            annual_cap_hit = contract['total_value'] // contract['contract_years']

    # Validate inputs
    if not all([overall_rating, position, age]):
        raise ValueError("Must provide overall_rating, position, and age")

    # Step 1: Base value from overall rating
    # Use power curve: 50 OVR = 0, 75 OVR = 100, 85 OVR = 300, 95 OVR = 700
    base_value = ((overall_rating - 50) ** 1.8) / 6.0
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
```

### 2.3 Draft Pick Valuation Method

```python
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
```

### 2.4 Trade Evaluation Method

```python
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
```

---

## Step 3: Test Strategy (30+ Tests)

**File**: `tests/transactions/test_trade_value_calculator.py`

### 3.1 Player Valuation Tests (10 tests)

```python
class TestPlayerValuation:
    """Test player value calculations"""

    def test_elite_qb_value(self):
        """Elite QB (95 OVR, age 28) should have very high value"""
        calc = TradeValueCalculator()
        value = calc.calculate_player_value(
            overall_rating=95,
            position='quarterback',
            age=28,
            contract_years_remaining=3,
            annual_cap_hit=45_000_000
        )
        # Elite QB in prime should be 600-800 value
        assert 600 <= value <= 800

    def test_aging_qb_decline(self):
        """QB value should decline significantly after age 33"""
        calc = TradeValueCalculator()

        prime_value = calc.calculate_player_value(
            overall_rating=90,
            position='quarterback',
            age=28
        )

        aging_value = calc.calculate_player_value(
            overall_rating=90,
            position='quarterback',
            age=35
        )

        # 35-year-old should be worth 60-70% of prime
        assert aging_value < prime_value * 0.75

    def test_rb_age_cliff(self):
        """RB should decline faster than QB with age"""
        calc = TradeValueCalculator()

        young_rb = calc.calculate_player_value(
            overall_rating=85,
            position='running_back',
            age=24
        )

        old_rb = calc.calculate_player_value(
            overall_rating=85,
            position='running_back',
            age=30
        )

        # 30-year-old RB should be worth <50% of 24-year-old
        assert old_rb < young_rb * 0.50

    def test_position_tier_premium(self):
        """QB should be worth ~2x more than RB at same rating"""
        calc = TradeValueCalculator()

        qb_value = calc.calculate_player_value(
            overall_rating=85,
            position='quarterback',
            age=27
        )

        rb_value = calc.calculate_player_value(
            overall_rating=85,
            position='running_back',
            age=27
        )

        # QB should be 1.5-2.0x RB value
        assert qb_value >= rb_value * 1.5

    def test_expiring_contract_penalty(self):
        """Expiring contract (1 year) should lower value"""
        calc = TradeValueCalculator()

        multi_year = calc.calculate_player_value(
            overall_rating=85,
            position='wide_receiver',
            age=26,
            contract_years_remaining=3,
            annual_cap_hit=15_000_000
        )

        expiring = calc.calculate_player_value(
            overall_rating=85,
            position='wide_receiver',
            age=26,
            contract_years_remaining=1,
            annual_cap_hit=15_000_000
        )

        # Expiring contract should be 10-20% lower
        assert expiring < multi_year * 0.92

    def test_bad_contract_penalty(self):
        """Severely overpaid player should have reduced value"""
        calc = TradeValueCalculator()

        fair_contract = calc.calculate_player_value(
            overall_rating=80,
            position='wide_receiver',
            age=28,
            contract_years_remaining=3,
            annual_cap_hit=10_000_000
        )

        bad_contract = calc.calculate_player_value(
            overall_rating=80,
            position='wide_receiver',
            age=28,
            contract_years_remaining=4,
            annual_cap_hit=25_000_000  # Very overpaid
        )

        # Bad contract should reduce value by 25-35%
        assert bad_contract < fair_contract * 0.75

    def test_rookie_vs_veteran(self):
        """Young player (22) vs peak veteran (28) at same rating"""
        calc = TradeValueCalculator()

        rookie = calc.calculate_player_value(
            overall_rating=82,
            position='linebacker',
            age=22
        )

        veteran = calc.calculate_player_value(
            overall_rating=82,
            position='linebacker',
            age=28
        )

        # Veteran in prime should be slightly more valuable
        assert veteran >= rookie * 0.95
        assert veteran <= rookie * 1.10

    def test_backup_vs_starter(self):
        """Backup (70 OVR) vs Starter (85 OVR) value gap"""
        calc = TradeValueCalculator()

        backup = calc.calculate_player_value(
            overall_rating=70,
            position='cornerback',
            age=25
        )

        starter = calc.calculate_player_value(
            overall_rating=85,
            position='cornerback',
            age=25
        )

        # Starter should be 4-6x more valuable
        assert starter >= backup * 4.0

    def test_team_need_multiplier(self):
        """Team with critical need should value player higher"""
        # This test requires mocking TeamNeedsAnalyzer
        # Placeholder for now
        pass

    def test_zero_ovr_gives_zero_value(self):
        """Player with 0 overall should have 0 value"""
        calc = TradeValueCalculator()
        value = calc.calculate_player_value(
            overall_rating=0,
            position='kicker',
            age=25
        )
        assert value == 0.0
```

### 3.2 Draft Pick Valuation Tests (8 tests)

```python
class TestDraftPickValuation:
    """Test draft pick value calculations"""

    def test_first_overall_pick_value(self):
        """#1 overall pick should have highest value"""
        calc = TradeValueCalculator()

        pick = DraftPick(
            round=1,
            year=2025,
            original_team_id=1,
            current_team_id=1,
            overall_pick_projected=1
        )

        value = calc.calculate_pick_value(pick)

        # Top pick should be worth 180-220 (scaled from 3000)
        assert 180 <= value <= 220

    def test_mid_first_round_value(self):
        """Pick #16 should be worth ~half of #1 pick"""
        calc = TradeValueCalculator()

        top_pick = DraftPick(round=1, year=2025, original_team_id=1, current_team_id=1)
        top_pick.overall_pick_projected = 1
        top_value = calc.calculate_pick_value(top_pick)

        mid_pick = DraftPick(round=1, year=2025, original_team_id=16, current_team_id=16)
        mid_pick.overall_pick_projected = 16
        mid_value = calc.calculate_pick_value(mid_pick)

        # Mid-1st should be 40-60% of top pick
        assert 0.40 * top_value <= mid_value <= 0.60 * top_value

    def test_second_round_vs_first(self):
        """Early 2nd round should be worth ~1/3 of late 1st"""
        calc = TradeValueCalculator()

        late_first = DraftPick(round=1, year=2025, original_team_id=32, current_team_id=32)
        late_first.overall_pick_projected = 32
        late_first_value = calc.calculate_pick_value(late_first)

        early_second = DraftPick(round=2, year=2025, original_team_id=1, current_team_id=1)
        early_second.overall_pick_projected = 33
        early_second_value = calc.calculate_pick_value(early_second)

        # Early 2nd should be 70-85% of late 1st (not huge drop)
        assert 0.70 * late_first_value <= early_second_value <= 0.90 * late_first_value

    def test_future_pick_discount(self):
        """Future picks should be discounted ~5% per year"""
        calc = TradeValueCalculator(current_year=2025)

        current = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)
        current.overall_pick_projected = 15
        current_value = calc.calculate_pick_value(current)

        future = DraftPick(round=1, year=2026, original_team_id=15, current_team_id=15)
        future.overall_pick_projected = 15
        future_value = calc.calculate_pick_value(future)

        # 2026 pick should be ~95% of 2025 pick
        assert 0.93 * current_value <= future_value <= 0.97 * current_value

    def test_two_years_out_discount(self):
        """2-year-future pick should be discounted ~10%"""
        calc = TradeValueCalculator(current_year=2025)

        current = DraftPick(round=1, year=2025, original_team_id=20, current_team_id=20)
        current.overall_pick_projected = 20
        current_value = calc.calculate_pick_value(current)

        two_years = DraftPick(round=1, year=2027, original_team_id=20, current_team_id=20)
        two_years.overall_pick_projected = 20
        two_years_value = calc.calculate_pick_value(two_years)

        # 2027 pick should be ~90% of 2025 pick (0.95^2)
        assert 0.88 * current_value <= two_years_value <= 0.92 * current_value

    def test_seventh_round_minimal_value(self):
        """7th round picks should have very low value"""
        calc = TradeValueCalculator()

        seventh = DraftPick(round=7, year=2025, original_team_id=15, current_team_id=15)
        seventh.overall_pick_projected = 220
        value = calc.calculate_pick_value(seventh)

        # 7th rounder should be worth < 5 units
        assert value < 5.0

    def test_projection_uncertainty_penalty(self):
        """Wide projection range should slightly reduce value"""
        calc = TradeValueCalculator()

        certain = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)
        certain.overall_pick_projected = 15
        certain.projected_range_min = 13
        certain.projected_range_max = 17
        certain_value = calc.calculate_pick_value(certain)

        uncertain = DraftPick(round=1, year=2026, original_team_id=15, current_team_id=15)
        uncertain.overall_pick_projected = 15
        uncertain.projected_range_min = 5
        uncertain.projected_range_max = 25
        uncertain_value = calc.calculate_pick_value(uncertain)

        # Uncertain pick should be 5-10% lower
        assert uncertain_value < certain_value * 0.95

    def test_team_record_projection(self):
        """Winning team's pick should project later"""
        pick = DraftPick(round=1, year=2025, original_team_id=15, current_team_id=15)

        # Good team (12-5 record)
        overall = pick.estimate_overall_pick(team_wins=12, team_losses=5)

        # Should project to late 1st round (pick 20-32)
        assert 20 <= overall <= 32
```

### 3.3 Trade Fairness Tests (7 tests)

```python
class TestTradeFairness:
    """Test trade evaluation and fairness ratings"""

    def test_perfectly_fair_trade(self):
        """Trade with 1.0 value ratio should be VERY_FAIR"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1,
            player_name="QB A",
            position="quarterback",
            overall_rating=85,
            age=28,
            trade_value=300.0
        )

        player2 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=2,
            player_name="QB B",
            position="quarterback",
            overall_rating=85,
            age=28,
            trade_value=300.0
        )

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[player1],
            team2_id=2,
            team2_assets=[player2]
        )

        assert proposal.value_ratio == 1.0
        assert proposal.fairness_rating == FairnessRating.VERY_FAIR
        assert proposal.is_acceptable()

    def test_slightly_unfair_trade(self):
        """Trade with 1.25 ratio should be SLIGHTLY_UNFAIR"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(asset_type=AssetType.PLAYER, trade_value=200.0)
        player2 = TradeAsset(asset_type=AssetType.PLAYER, trade_value=250.0)

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[player1],
            team2_id=2,
            team2_assets=[player2]
        )

        assert proposal.value_ratio == 1.25
        assert proposal.fairness_rating == FairnessRating.SLIGHTLY_UNFAIR
        assert not proposal.is_acceptable()

    def test_very_unfair_trade(self):
        """Trade with 1.5 ratio should be VERY_UNFAIR"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(asset_type=AssetType.PLAYER, trade_value=200.0)
        player2 = TradeAsset(asset_type=AssetType.PLAYER, trade_value=300.0)

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[player1],
            team2_id=2,
            team2_assets=[player2]
        )

        assert proposal.value_ratio == 1.5
        assert proposal.fairness_rating == FairnessRating.VERY_UNFAIR
        assert not proposal.is_acceptable()

    def test_multi_asset_trade(self):
        """Trade with multiple players and picks"""
        calc = TradeValueCalculator()

        # Team 1 gives: WR (200) + 2nd round pick (50)
        wr = TradeAsset(asset_type=AssetType.PLAYER, trade_value=200.0)
        pick2 = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=50.0)

        # Team 2 gives: 1st round pick (150) + 3rd round pick (25) + 4th round (15)
        pick1 = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=150.0)
        pick3 = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=25.0)
        pick4 = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=15.0)

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[wr, pick2],  # Total: 250
            team2_id=2,
            team2_assets=[pick1, pick3, pick4]  # Total: 190
        )

        # Team 1 getting 190, giving 250 = 0.76 ratio (slightly unfair to team 1)
        assert 0.75 <= proposal.value_ratio <= 0.77
        assert proposal.fairness_rating == FairnessRating.SLIGHTLY_UNFAIR

    def test_player_for_picks_fair(self):
        """Elite player for multiple 1st round picks"""
        calc = TradeValueCalculator()

        # Elite WR worth 350
        elite_wr = TradeAsset(asset_type=AssetType.PLAYER, trade_value=350.0)

        # Two 1st rounders worth 150 + 100 = 250
        # Plus 2nd rounder worth 50 = 300 total
        pick1a = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=150.0)
        pick1b = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=100.0)
        pick2 = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=50.0)

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[elite_wr],
            team2_id=2,
            team2_assets=[pick1a, pick1b, pick2]
        )

        # 300 / 350 = 0.857 (FAIR range)
        assert proposal.fairness_rating in [FairnessRating.FAIR, FairnessRating.VERY_FAIR]

    def test_zero_value_asset(self):
        """Trade including worthless asset"""
        calc = TradeValueCalculator()

        good_player = TradeAsset(asset_type=AssetType.PLAYER, trade_value=200.0)
        bad_player = TradeAsset(asset_type=AssetType.PLAYER, trade_value=0.0)

        proposal = calc.evaluate_trade(
            team1_id=1,
            team1_assets=[bad_player],
            team2_id=2,
            team2_assets=[good_player]
        )

        # Infinite ratio = VERY_UNFAIR
        assert proposal.fairness_rating == FairnessRating.VERY_UNFAIR

    def test_get_summary_format(self):
        """Trade proposal summary should be human-readable"""
        calc = TradeValueCalculator()

        player1 = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Patrick Mahomes",
            position="quarterback",
            overall_rating=99,
            age=28,
            trade_value=700.0
        )

        pick = TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=180.0)

        proposal = calc.evaluate_trade(
            team1_id=15,  # Chiefs
            team1_assets=[player1],
            team2_id=8,   # Broncos
            team2_assets=[pick]
        )

        summary = proposal.get_summary()

        assert "Patrick Mahomes" in summary
        assert "Value:" in summary
        assert "Value Ratio:" in summary
        assert "Acceptable:" in summary
```

### 3.4 Integration Tests (5 tests)

```python
class TestCalculatorIntegration:
    """Test calculator with real data and scenarios"""

    def test_tyreek_hill_trade(self):
        """Recreate Tyreek Hill trade (2022)"""
        # Tyreek Hill: 97 OVR WR, age 28
        # Chiefs received: 2022 1st (29), 2022 2nd (50), 2023 1st (21), 2023 2nd
        calc = TradeValueCalculator(current_year=2022)

        tyreek = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_name="Tyreek Hill",
            position="wide_receiver",
            overall_rating=97,
            age=28,
            trade_value=calc.calculate_player_value(
                overall_rating=97,
                position='wide_receiver',
                age=28,
                contract_years_remaining=0  # Needed new contract
            )
        )

        # Create draft picks
        pick1_2022 = DraftPick(round=1, year=2022, original_team_id=18, current_team_id=18)
        pick1_2022.overall_pick_projected = 29

        pick2_2022 = DraftPick(round=2, year=2022, original_team_id=18, current_team_id=18)
        pick2_2022.overall_pick_projected = 50

        pick1_2023 = DraftPick(round=1, year=2023, original_team_id=18, current_team_id=18)
        pick1_2023.overall_pick_projected = 21

        pick2_2023 = DraftPick(round=2, year=2023, original_team_id=18, current_team_id=18)
        pick2_2023.overall_pick_projected = 54

        # Calculate pick values
        picks = [
            TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick1_2022)),
            TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick2_2022)),
            TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick1_2023)),
            TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick2_2023)),
        ]

        proposal = calc.evaluate_trade(
            team1_id=15,  # Chiefs
            team1_assets=[tyreek],
            team2_id=18,  # Dolphins
            team2_assets=picks
        )

        # This trade should be evaluated as FAIR or VERY_FAIR
        assert proposal.fairness_rating in [FairnessRating.FAIR, FairnessRating.VERY_FAIR]

        # Value ratio should be 0.8-1.2
        assert 0.80 <= proposal.value_ratio <= 1.20

    def test_with_database_integration(self):
        """Test with real database player lookup"""
        # Requires database setup - placeholder
        pass

    def test_with_team_needs_integration(self):
        """Test with TeamNeedsAnalyzer integration"""
        # Requires mocking - placeholder
        pass

    def test_salary_cap_validation(self):
        """Test that trades respect salary cap"""
        # Future enhancement - placeholder
        pass

    def test_roster_minimums_validation(self):
        """Test that teams maintain minimum roster requirements"""
        # Future enhancement - placeholder
        pass
```

---

## Step 4: Interactive Demo

**File**: `demo/trade_value_demo/trade_value_demo.py`

### 4.1 Demo Structure

```python
"""
Interactive Trade Value Calculator Demo

Demonstrates 5 trade scenarios:
1. Elite QB for multiple 1st round picks (Russell Wilson style)
2. Star WR for 1st + 2nd round picks (Tyreek Hill style)
3. Draft position trade-up (moving up 10 spots in 1st round)
4. Salary dump trade (negative value player + pick compensation)
5. Multi-asset blockbuster (3-for-3 trade)
"""

def main():
    """Run interactive demo"""
    print("=" * 80)
    print("TRADE VALUE CALCULATOR - PHASE 1.2 DEMO")
    print("=" * 80)
    print()

    calc = TradeValueCalculator(current_year=2025)

    # Scenario 1: Elite QB Trade
    print_scenario_1(calc)

    # Scenario 2: Star WR Trade
    print_scenario_2(calc)

    # Scenario 3: Draft Trade-Up
    print_scenario_3(calc)

    # Scenario 4: Salary Dump
    print_scenario_4(calc)

    # Scenario 5: Blockbuster Multi-Asset
    print_scenario_5(calc)

    # Interactive calculator
    run_interactive_mode(calc)

def print_scenario_1(calc):
    """Scenario 1: Elite QB for multiple 1st rounders"""
    print("SCENARIO 1: Elite QB Trade (Russell Wilson Style)")
    print("-" * 80)

    # Russell Wilson equivalent: 90 OVR QB, age 33, expiring contract
    qb = calc.calculate_player_value(
        overall_rating=90,
        position='quarterback',
        age=33,
        contract_years_remaining=1,
        annual_cap_hit=35_000_000
    )

    # Picks: 2025 1st (9th), 2025 2nd (40th), 2026 1st (5th), 2026 2nd (37th)
    pick1_2025 = DraftPick(round=1, year=2025, original_team_id=8, current_team_id=8)
    pick1_2025.overall_pick_projected = 9

    pick2_2025 = DraftPick(round=2, year=2025, original_team_id=8, current_team_id=8)
    pick2_2025.overall_pick_projected = 40

    pick1_2026 = DraftPick(round=1, year=2026, original_team_id=8, current_team_id=8)
    pick1_2026.overall_pick_projected = 5

    pick2_2026 = DraftPick(round=2, year=2026, original_team_id=8, current_team_id=8)
    pick2_2026.overall_pick_projected = 37

    # Calculate
    qb_asset = TradeAsset(
        asset_type=AssetType.PLAYER,
        player_name="Elite QB",
        position="quarterback",
        overall_rating=90,
        age=33,
        trade_value=qb
    )

    pick_assets = [
        TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick1_2025)),
        TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick2_2025)),
        TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick1_2026)),
        TradeAsset(asset_type=AssetType.DRAFT_PICK, trade_value=calc.calculate_pick_value(pick2_2026)),
    ]

    proposal = calc.evaluate_trade(
        team1_id=27,  # Seahawks
        team1_assets=[qb_asset],
        team2_id=8,   # Broncos
        team2_assets=pick_assets
    )

    print(proposal.get_summary())
    print()
```

### 4.2 Interactive Calculator Mode

```python
def run_interactive_mode(calc):
    """Run interactive calculator for user input"""
    print("=" * 80)
    print("INTERACTIVE MODE")
    print("=" * 80)
    print()

    while True:
        print("Options:")
        print("1. Calculate player value")
        print("2. Calculate draft pick value")
        print("3. Evaluate complete trade")
        print("4. Exit")

        choice = input("\nEnter choice (1-4): ")

        if choice == '1':
            interactive_player_value(calc)
        elif choice == '2':
            interactive_pick_value(calc)
        elif choice == '3':
            interactive_trade_eval(calc)
        elif choice == '4':
            break

        print()

def interactive_player_value(calc):
    """Get player value from user input"""
    print("\n--- Player Valuation ---")

    overall = int(input("Overall rating (0-100): "))
    position = input("Position (e.g., quarterback, wide_receiver): ")
    age = int(input("Age: "))

    contract_input = input("Include contract? (y/n): ")
    if contract_input.lower() == 'y':
        years = int(input("Contract years remaining: "))
        cap_hit = int(input("Annual cap hit ($M): ")) * 1_000_000
    else:
        years = None
        cap_hit = None

    value = calc.calculate_player_value(
        overall_rating=overall,
        position=position,
        age=age,
        contract_years_remaining=years,
        annual_cap_hit=cap_hit
    )

    print(f"\nTrade Value: {value:.1f} units")
    print(f"Equivalent to: {_value_to_description(value)}")

def _value_to_description(value: float) -> str:
    """Convert value to descriptive comparison"""
    if value >= 600:
        return "Elite franchise QB"
    elif value >= 400:
        return "All-Pro player"
    elif value >= 300:
        return "Pro Bowl player"
    elif value >= 200:
        return "Good starter"
    elif value >= 100:
        return "Average starter"
    elif value >= 50:
        return "Solid backup"
    else:
        return "Depth player"
```

---

## Step 5: Real-World Benchmarking

**File**: `demo/trade_value_demo/real_world_trades.json`

### 5.1 Historical Trade Database

```json
{
  "trades": [
    {
      "id": 1,
      "name": "Tyreek Hill Trade",
      "year": 2022,
      "team1": {"id": 15, "name": "Kansas City Chiefs"},
      "team2": {"id": 18, "name": "Miami Dolphins"},
      "team1_gives": [
        {
          "type": "player",
          "name": "Tyreek Hill",
          "position": "wide_receiver",
          "overall": 97,
          "age": 28,
          "contract_years": 0
        }
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2022, "overall": 29},
        {"type": "pick", "round": 2, "year": 2022, "overall": 50},
        {"type": "pick", "round": 1, "year": 2023, "overall": 21},
        {"type": "pick", "round": 2, "year": 2023, "overall": 54}
      ],
      "expected_ratio_range": [0.85, 1.15],
      "notes": "Elite WR in prime, needed new contract"
    },
    {
      "id": 2,
      "name": "Russell Wilson Trade",
      "year": 2022,
      "team1": {"id": 27, "name": "Seattle Seahawks"},
      "team2": {"id": 8, "name": "Denver Broncos"},
      "team1_gives": [
        {
          "type": "player",
          "name": "Russell Wilson",
          "position": "quarterback",
          "overall": 90,
          "age": 33,
          "contract_years": 2
        }
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2022, "overall": 9},
        {"type": "pick", "round": 2, "year": 2022, "overall": 40},
        {"type": "pick", "round": 1, "year": 2023, "overall": 5},
        {"type": "pick", "round": 2, "year": 2023, "overall": 37},
        {"type": "pick", "round": 2, "year": 2024, "overall": 42},
        {
          "type": "player",
          "name": "Drew Lock",
          "position": "quarterback",
          "overall": 72,
          "age": 25,
          "contract_years": 1
        },
        {
          "type": "player",
          "name": "Shelby Harris",
          "position": "defensive_tackle",
          "overall": 78,
          "age": 30,
          "contract_years": 2
        },
        {
          "type": "player",
          "name": "Noah Fant",
          "position": "tight_end",
          "overall": 81,
          "age": 24,
          "contract_years": 1
        }
      ],
      "expected_ratio_range": [0.80, 1.20],
      "notes": "Blockbuster QB trade, aging star"
    },
    {
      "id": 3,
      "name": "Jalen Ramsey Trade",
      "year": 2019,
      "team1": {"id": 13, "name": "Jacksonville Jaguars"},
      "team2": {"id": 17, "name": "Los Angeles Rams"},
      "team1_gives": [
        {
          "type": "player",
          "name": "Jalen Ramsey",
          "position": "cornerback",
          "overall": 93,
          "age": 24,
          "contract_years": 1
        }
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2020, "overall": 20},
        {"type": "pick", "round": 1, "year": 2021, "overall": 25}
      ],
      "expected_ratio_range": [0.90, 1.10],
      "notes": "Elite young CB, expiring contract"
    },
    {
      "id": 4,
      "name": "Khalil Mack Trade",
      "year": 2018,
      "team1": {"id": 16, "name": "Oakland Raiders"},
      "team2": {"id": 5, "name": "Chicago Bears"},
      "team1_gives": [
        {
          "type": "player",
          "name": "Khalil Mack",
          "position": "edge_rusher",
          "overall": 95,
          "age": 27,
          "contract_years": 1
        }
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2019, "overall": 24},
        {"type": "pick", "round": 1, "year": 2020, "overall": 19},
        {"type": "pick", "round": 6, "year": 2020, "overall": 201}
      ],
      "expected_ratio_range": [0.85, 1.15],
      "notes": "Elite edge rusher in prime, needed new contract"
    },
    {
      "id": 5,
      "name": "Amari Cooper Trade",
      "year": 2018,
      "team1": {"id": 16, "name": "Oakland Raiders"},
      "team2": {"id": 10, "name": "Dallas Cowboys"},
      "team1_gives": [
        {
          "type": "player",
          "name": "Amari Cooper",
          "position": "wide_receiver",
          "overall": 85,
          "age": 24,
          "contract_years": 1
        }
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2019, "overall": 27}
      ],
      "expected_ratio_range": [0.85, 1.15],
      "notes": "Young WR mid-season trade"
    },
    {
      "id": 6,
      "name": "Stefon Diggs Trade",
      "year": 2020,
      "team1": {"id": 19, "name": "Minnesota Vikings"},
      "team2": {"id": 4, "name": "Buffalo Bills"},
      "team1_gives": [
        {
          "type": "player",
          "name": "Stefon Diggs",
          "position": "wide_receiver",
          "overall": 90,
          "age": 26,
          "contract_years": 3
        }
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2020, "overall": 22},
        {"type": "pick", "round": 5, "year": 2020, "overall": 149},
        {"type": "pick", "round": 6, "year": 2020, "overall": 180},
        {"type": "pick", "round": 4, "year": 2021, "overall": 120}
      ],
      "expected_ratio_range": [0.85, 1.15],
      "notes": "Pro Bowl WR with team control"
    },
    {
      "id": 7,
      "name": "49ers Trade Up (Pick #2 → #3)",
      "year": 2021,
      "team1": {"id": 18, "name": "Miami Dolphins"},
      "team2": {"id": 26, "name": "San Francisco 49ers"},
      "team1_gives": [
        {"type": "pick", "round": 1, "year": 2021, "overall": 3}
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2021, "overall": 12},
        {"type": "pick", "round": 1, "year": 2022, "overall": 29},
        {"type": "pick", "round": 3, "year": 2023, "overall": 70}
      ],
      "expected_ratio_range": [0.95, 1.05],
      "notes": "Classic trade-up, paid heavy premium to move up 9 spots"
    },
    {
      "id": 8,
      "name": "Saints Trade Up (Pick #12 → #6)",
      "year": 2022,
      "team1": {"id": 25, "name": "Washington Commanders"},
      "team2": {"id": 20, "name": "New Orleans Saints"},
      "team1_gives": [
        {"type": "pick", "round": 1, "year": 2022, "overall": 11}
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2022, "overall": 16},
        {"type": "pick", "round": 3, "year": 2022, "overall": 98},
        {"type": "pick", "round": 1, "year": 2023, "overall": 19},
        {"type": "pick", "round": 2, "year": 2024, "overall": 40}
      ],
      "expected_ratio_range": [0.70, 0.90],
      "notes": "Steep premium to move up 5 spots in top 15"
    },
    {
      "id": 9,
      "name": "DeAndre Hopkins Trade",
      "year": 2020,
      "team1": {"id": 11, "name": "Houston Texans"},
      "team2": {"id": 1, "name": "Arizona Cardinals"},
      "team1_gives": [
        {
          "type": "player",
          "name": "DeAndre Hopkins",
          "position": "wide_receiver",
          "overall": 95,
          "age": 27,
          "contract_years": 3
        }
      ],
      "team2_gives": [
        {
          "type": "player",
          "name": "David Johnson",
          "position": "running_back",
          "overall": 75,
          "age": 28,
          "contract_years": 2,
          "cap_hit": 10500000
        },
        {"type": "pick", "round": 2, "year": 2020, "overall": 40},
        {"type": "pick", "round": 4, "year": 2021, "overall": 110}
      ],
      "expected_ratio_range": [1.20, 1.50],
      "notes": "Lopsided trade - elite WR for aging RB on bad contract"
    },
    {
      "id": 10,
      "name": "Davante Adams Trade",
      "year": 2022,
      "team1": {"id": 12, "name": "Green Bay Packers"},
      "team2": {"id": 16, "name": "Las Vegas Raiders"},
      "team1_gives": [
        {
          "type": "player",
          "name": "Davante Adams",
          "position": "wide_receiver",
          "overall": 96,
          "age": 29,
          "contract_years": 0
        }
      ],
      "team2_gives": [
        {"type": "pick", "round": 1, "year": 2022, "overall": 22},
        {"type": "pick", "round": 2, "year": 2022, "overall": 53}
      ],
      "expected_ratio_range": [0.85, 1.15],
      "notes": "Elite WR in late prime, no contract"
    }
  ]
}
```

### 5.2 Benchmarking Script

**File**: `demo/trade_value_demo/benchmark_trades.py`

```python
"""
Real-World Trade Benchmarking Script

Evaluates calculator accuracy against 10 historical NFL trades.
"""

import json
from src.transactions.trade_value_calculator import TradeValueCalculator
from src.transactions.models import TradeAsset, DraftPick, AssetType

def load_historical_trades():
    """Load historical trades from JSON"""
    with open('demo/trade_value_demo/real_world_trades.json', 'r') as f:
        data = json.load(f)
    return data['trades']

def benchmark_calculator():
    """Run calculator on all historical trades"""
    trades = load_historical_trades()
    calc = TradeValueCalculator(current_year=2025)

    results = []

    for trade in trades:
        print(f"\n{'='*80}")
        print(f"Evaluating: {trade['name']} ({trade['year']})")
        print(f"{'='*80}")

        # Build assets for team1
        team1_assets = build_assets(trade['team1_gives'], calc, trade['year'])

        # Build assets for team2
        team2_assets = build_assets(trade['team2_gives'], calc, trade['year'])

        # Evaluate trade
        proposal = calc.evaluate_trade(
            team1_id=trade['team1']['id'],
            team1_assets=team1_assets,
            team2_id=trade['team2']['id'],
            team2_assets=team2_assets
        )

        # Check if within expected range
        expected_min, expected_max = trade['expected_ratio_range']
        within_range = expected_min <= proposal.value_ratio <= expected_max

        result = {
            'trade_name': trade['name'],
            'calculated_ratio': proposal.value_ratio,
            'expected_range': trade['expected_ratio_range'],
            'within_range': within_range,
            'fairness': proposal.fairness_rating.value,
            'team1_value': proposal.team1_total_value,
            'team2_value': proposal.team2_total_value
        }
        results.append(result)

        # Print results
        print(f"\n{proposal.get_summary()}")
        print(f"\nExpected Ratio: {expected_min:.2f} - {expected_max:.2f}")
        print(f"Calculated Ratio: {proposal.value_ratio:.3f}")
        print(f"Within Expected Range: {'✓ YES' if within_range else '✗ NO'}")
        print(f"Difference: {abs(proposal.value_ratio - (expected_min + expected_max)/2) * 100:.1f}%")

    # Print summary
    print(f"\n\n{'='*80}")
    print("BENCHMARKING SUMMARY")
    print(f"{'='*80}")

    total_trades = len(results)
    within_range_count = sum(1 for r in results if r['within_range'])
    accuracy = (within_range_count / total_trades) * 100

    print(f"\nTotal Trades Evaluated: {total_trades}")
    print(f"Within Expected Range: {within_range_count}/{total_trades} ({accuracy:.1f}%)")
    print(f"\nTarget Accuracy: 85%+")
    print(f"Status: {'✓ PASS' if accuracy >= 85 else '✗ NEEDS CALIBRATION'}")

    return results

def build_assets(asset_list, calc, trade_year):
    """Convert asset definitions to TradeAsset objects"""
    assets = []

    for asset_def in asset_list:
        if asset_def['type'] == 'player':
            value = calc.calculate_player_value(
                overall_rating=asset_def['overall'],
                position=asset_def['position'],
                age=asset_def['age'],
                contract_years_remaining=asset_def.get('contract_years', 3),
                annual_cap_hit=asset_def.get('cap_hit', None)
            )

            asset = TradeAsset(
                asset_type=AssetType.PLAYER,
                player_name=asset_def['name'],
                position=asset_def['position'],
                overall_rating=asset_def['overall'],
                age=asset_def['age'],
                trade_value=value
            )

        elif asset_def['type'] == 'pick':
            pick = DraftPick(
                round=asset_def['round'],
                year=asset_def['year'],
                original_team_id=1,  # Placeholder
                current_team_id=1
            )
            pick.overall_pick_projected = asset_def['overall']

            value = calc.calculate_pick_value(pick)

            asset = TradeAsset(
                asset_type=AssetType.DRAFT_PICK,
                draft_pick=pick,
                trade_value=value
            )

        assets.append(asset)

    return assets

if __name__ == "__main__":
    benchmark_calculator()
```

---

## Step 6: Success Criteria

### Functional Requirements
- ✅ Calculate player trade values (0-800 range)
- ✅ Calculate draft pick values using Jimmy Johnson chart
- ✅ Evaluate trade fairness (0.8-1.2 acceptable range)
- ✅ Support multi-asset trades (players + picks)
- ✅ Account for age curves by position
- ✅ Account for contract value/length
- ✅ Context-aware valuations (team needs)
- ✅ Future pick discounting (5% per year)

### Testing Requirements
- ✅ 30+ unit tests with 100% pass rate
- ✅ Player valuation tests (10 tests)
- ✅ Pick valuation tests (8 tests)
- ✅ Fairness evaluation tests (7 tests)
- ✅ Integration tests (5 tests)

### Benchmarking Requirements
- ✅ 10 real-world NFL trades evaluated
- ✅ 85%+ accuracy (value ratios within expected ranges)
- ✅ Tyreek Hill trade within ±15%
- ✅ Russell Wilson trade within ±20%
- ✅ Pick trade-ups within ±10%

### Demo Requirements
- ✅ 5 interactive scenarios
- ✅ User input calculator mode
- ✅ Human-readable trade summaries
- ✅ Value-to-description mappings

---

## Implementation Checklist

**Week 1: Core System**
- [ ] Implement data models (TradeAsset, DraftPick, TradeProposal)
- [ ] Implement Jimmy Johnson draft chart
- [ ] Implement TradeValueCalculator class structure
- [ ] Implement player valuation algorithm
- [ ] Implement pick valuation algorithm

**Week 2: Testing**
- [ ] Write 10 player valuation tests
- [ ] Write 8 pick valuation tests
- [ ] Write 7 fairness tests
- [ ] Write 5 integration tests
- [ ] Achieve 100% test pass rate

**Week 3: Demo & Benchmarking**
- [ ] Create 5 interactive demo scenarios
- [ ] Build interactive calculator mode
- [ ] Create real-world trades JSON database
- [ ] Implement benchmarking script
- [ ] Achieve 85%+ benchmark accuracy

**Week 4: Polish & Documentation**
- [ ] Calibrate formulas based on benchmarking
- [ ] Add mathematical documentation
- [ ] Create usage examples
- [ ] Integration prep for Phase 1.3

---

## Integration with Existing Systems

### Phase 1.1 (GM Archetypes)
- GM `draft_pick_value` trait influences pick valuations
- GM `risk_tolerance` affects acceptable fairness ranges
- GM `win_now_mentality` modifies age curve importance

### Offseason Systems
- `TeamNeedsAnalyzer` provides context for need multipliers
- `MarketValueCalculator` informs contract valuation
- `CapCalculator` validates cap space for trades

### Event System
- Prepare for `PlayerTradeEvent` creation (Phase 1.3)
- Trade proposals will generate events
- Cap validation via `EventCapBridge`

---

## Next Phase Preview

**Phase 1.3: Trade Proposal Generator & AI Manager**
- Generate trade proposals based on team needs + GM archetype
- Evaluate incoming trade offers (accept/reject logic)
- Daily transaction probability system
- Integration with `SeasonCycleController`

Phase 1.2 provides the objective valuation foundation that Phase 1.3 will use for AI decision-making.
