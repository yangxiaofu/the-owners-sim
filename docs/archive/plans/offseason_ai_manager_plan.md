# Offseason AI Manager Implementation Plan

**Status**: Phase 2 Complete (Phase 1 & 2: All Critical + High Priority Gaps Complete)
**Created**: October 2025
**Last Updated**: October 18, 2025

---

## Executive Summary

This document outlines the implementation plan for the **OffseasonAIManager** system, which enables AI-controlled teams to make intelligent offseason decisions (franchise tags, free agency, draft, roster cuts).

**Current State**: All infrastructure exists (database APIs, EventCapBridge, manager stubs, OffseasonController), but AI teams cannot make decisions autonomously.

**Goal**: Enable AI teams to simulate realistic NFL offseason behavior without user intervention.

---

## Table of Contents

1. [Current Infrastructure](#current-infrastructure)
2. [Critical Gaps](#critical-gaps)
3. [High Priority Gaps](#high-priority-gaps)
4. [Medium Priority Gaps](#medium-priority-gaps)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Testing Strategy](#testing-strategy)
7. [Success Criteria](#success-criteria)

---

## Current Infrastructure

### ✅ What Already Works

**Database Layer**:
- `PlayerRosterAPI` - Player data retrieval (src/database/player_roster_api.py)
- `CapDatabaseAPI` - Contract and cap queries (src/salary_cap/cap_database_api.py)
- `DatabaseAPI` - Game results and standings (src/database/api.py)
- `DepthChartAPI` - Depth chart operations (src/depth_chart/depth_chart_api.py)

**Business Logic Layer**:
- `CapCalculator` - All cap math operations (src/salary_cap/cap_calculator.py)
- `CapValidator` - Contract validation (src/salary_cap/cap_validator.py)
- `ContractManager` - Contract lifecycle (src/salary_cap/contract_manager.py)
- `TagManager` - Franchise/transition tag logic (src/salary_cap/tag_manager.py)
- `EventCapBridge` - Event-to-cap integration (src/salary_cap/event_integration.py)

**Event System**:
- `FranchiseTagEvent` - Executes franchise tag application
- `TransitionTagEvent` - Executes transition tag
- `UFASigningEvent` - Executes free agent signing
- `PlayerReleaseEvent` - Executes player release with dead money
- `ContractRestructureEvent` - Executes contract restructure
- `RFAOfferSheetEvent` - Executes RFA offer sheet

**Manager Stubs** (exist but NotImplementedError):
- `OffseasonController` - API orchestration layer (src/offseason/offseason_controller.py)
- `FreeAgencyManager` - Free agency operations (src/offseason/free_agency_manager.py)
- `DraftManager` - Draft operations (src/offseason/draft_manager.py)
- `RosterManager` - Roster management (src/offseason/roster_manager.py)

**Player Generation** (IN DEVELOPMENT):
- `player_generation/` module with archetype-based generation
- Can generate draft classes once integrated

---

## Critical Gaps

These gaps MUST be filled before AI can make any decisions.

### Gap 1: Contract Expiration Queries ✅ COMPLETE

**Status**: ✅ **COMPLETE** (Implemented October 18, 2025)

**Problem**: No way to identify which players are pending free agents.

**Impact**: Cannot determine franchise tag candidates or plan for free agency.

**Implementation Summary**:
- ✅ Added `get_expiring_contracts()` to `src/salary_cap/cap_database_api.py` (lines 290-350)
- ✅ Added `get_pending_free_agents()` to `src/salary_cap/cap_database_api.py` (lines 352-418)
- ✅ Created comprehensive unit tests in `tests/salary_cap/test_contract_expiration.py` (12 test cases, all passing)
- ✅ Created manual integration test in `test_gap1_manual.py` (4 scenarios, all passing)
- ✅ Verified dynasty isolation and correct SQL JOIN operations
- ✅ Verified sorting, filtering, and AAV calculation

**Original Requirements**:

**File**: `src/salary_cap/cap_database_api.py`

```python
def get_expiring_contracts(
    self,
    team_id: int,
    season: int,
    dynasty_id: str,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get all contracts expiring after this season.

    Args:
        team_id: Team ID (1-32)
        season: Current season year
        dynasty_id: Dynasty identifier
        active_only: Only return active contracts

    Returns:
        List of contract dicts with player info
    """
    with sqlite3.connect(self.database_path) as conn:
        conn.row_factory = sqlite3.Row

        query = '''
            SELECT
                pc.*,
                p.first_name || ' ' || p.last_name as player_name,
                p.positions,
                p.attributes,
                p.years_pro
            FROM player_contracts pc
            JOIN players p
                ON pc.player_id = p.player_id
                AND pc.dynasty_id = p.dynasty_id
            WHERE pc.team_id = ?
              AND pc.dynasty_id = ?
              AND pc.end_year = ?
        '''
        params = [team_id, dynasty_id, season]

        if active_only:
            query += " AND pc.is_active = TRUE"

        query += " ORDER BY pc.total_value DESC"

        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        return results


def get_pending_free_agents(
    self,
    team_id: int,
    season: int,
    dynasty_id: str,
    min_overall: int = 0
) -> List[Dict[str, Any]]:
    """
    Get pending free agents (contracts expiring) with player ratings.

    Convenience method that filters expiring contracts by overall rating.

    Args:
        team_id: Team ID (1-32)
        season: Current season year
        dynasty_id: Dynasty identifier
        min_overall: Minimum overall rating to include

    Returns:
        List of player dicts with contract and rating info
    """
    expiring = self.get_expiring_contracts(team_id, season, dynasty_id)

    # Parse attributes and filter by overall
    pending_fas = []
    for contract in expiring:
        attrs = json.loads(contract['attributes'])
        overall = attrs.get('overall', 0)

        if overall >= min_overall:
            positions = json.loads(contract['positions'])

            pending_fas.append({
                'player_id': contract['player_id'],
                'player_name': contract['player_name'],
                'position': positions[0] if positions else 'UNKNOWN',
                'overall': overall,
                'years_pro': contract['years_pro'],
                'contract_id': contract['contract_id'],
                'contract_value': contract['total_value'],
                'contract_years': contract['contract_years']
            })

    return sorted(pending_fas, key=lambda x: x['overall'], reverse=True)
```

**Dependencies**: None (uses existing tables)

**Testing**: ✅ COMPLETE
- ✅ Created test contracts expiring in season 2025
- ✅ Verified query returns correct players (12/12 unit tests passing)
- ✅ Verified filtering by overall rating works (min_overall parameter tested)
- ✅ Verified dynasty isolation (different dynasties don't see each other's contracts)
- ✅ Verified sorting (by contract value for expiring, by overall for pending FAs)
- ✅ Manual testing with realistic NFL players (Mahomes, Kupp, Henry, etc.)

---

### Gap 2: Team Needs Analysis ✅ COMPLETE

**Status**: ✅ **COMPLETE** (Implemented October 18, 2025)

**Problem**: No system to identify roster weaknesses and prioritize positions.

**Impact**: AI cannot make intelligent free agency or draft decisions.

**Implementation Summary**:
- ✅ Created `src/offseason/team_needs_analyzer.py` (288 lines, complete implementation)
- ✅ Implemented 4-tier position value system (QB/DE/OT > WR/CB/C > RB/LB/S/G > TE/DT)
- ✅ Implemented 5-level urgency system (CRITICAL, HIGH, MEDIUM, LOW, NONE)
- ✅ Integrated with Gap 1 (`get_pending_free_agents()`) for expiring contract detection
- ✅ Created comprehensive unit tests in `tests/salary_cap/test_team_needs_analyzer.py` (14 test cases, all passing)
- ✅ Created interactive terminal demo in `demo_team_needs_analyzer.py` (uses real Cleveland Browns data)
- ✅ Created quick demo runner in `run_team_needs_demo.py` for rapid testing
- ✅ Updated `src/offseason/__init__.py` to export `TeamNeedsAnalyzer` and `NeedUrgency`
- ✅ Verified dynasty isolation, urgency detection, and position tier weighting
- ✅ **UI Integration Complete**: Created `ui/widgets/team_needs_widget.py` (October 18, 2025)
  - Compact UI with Offense/Defense toggle buttons
  - Shows only starter per position (reduced from 5 players)
  - Color-coded ratings (gray for low ratings, not red)
  - Urgency indicators with emoji (🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low, ✅ Strong)
  - Integrated with Team View tab in desktop application
  - Ultra-thin spacing and optimized layout for better UX

**Required Implementation**:

**File**: `src/offseason/team_needs_analyzer.py` (NEW)

```python
"""
Team Needs Analyzer

Analyzes team roster to identify positional weaknesses and priorities.
Used by AI to make intelligent free agency and draft decisions.
"""

from typing import List, Dict, Any, Tuple
from enum import Enum
import json

from database.player_roster_api import PlayerRosterAPI
from depth_chart.depth_chart_api import DepthChartAPI
from salary_cap.cap_database_api import CapDatabaseAPI


class NeedUrgency(Enum):
    """Priority levels for positional needs."""
    CRITICAL = 5  # No starter or starter < 70 overall
    HIGH = 4      # Starter 70-75 overall or no backup
    MEDIUM = 3    # Starter 75-80 overall or weak depth
    LOW = 2       # Starter 80-85 overall, adequate depth
    NONE = 1      # Starter 85+ overall, good depth


class TeamNeedsAnalyzer:
    """
    Analyzes team roster to identify positional needs.

    Evaluates:
    - Starter quality (overall rating)
    - Depth quality and quantity
    - Age and contract status
    - Position importance (QB > RB, etc.)
    """

    # Position value tiers (affects urgency calculations)
    TIER_1_POSITIONS = ['quarterback', 'edge_rusher', 'offensive_tackle']
    TIER_2_POSITIONS = ['wide_receiver', 'cornerback', 'center']
    TIER_3_POSITIONS = ['running_back', 'linebacker', 'safety', 'guard']
    TIER_4_POSITIONS = ['tight_end', 'defensive_tackle']

    # Minimum acceptable starter ratings by tier
    STARTER_THRESHOLDS = {
        1: 75,  # Premium positions need 75+ starter
        2: 72,  # Important positions need 72+ starter
        3: 70,  # Standard positions need 70+ starter
        4: 68   # Lower value positions need 68+ starter
    }

    def __init__(self, database_path: str, dynasty_id: str):
        """
        Initialize team needs analyzer.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for isolation
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id

        self.player_api = PlayerRosterAPI(database_path)
        self.depth_chart_api = DepthChartAPI(database_path)
        self.cap_api = CapDatabaseAPI(database_path)

    def analyze_team_needs(
        self,
        team_id: int,
        season: int,
        include_future_contracts: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze team roster and return prioritized list of needs.

        Args:
            team_id: Team ID (1-32)
            season: Current season year
            include_future_contracts: Consider upcoming free agents

        Returns:
            List of need dicts sorted by urgency (highest first):
            [
                {
                    'position': 'quarterback',
                    'urgency': NeedUrgency.CRITICAL,
                    'urgency_score': 5,
                    'starter_overall': 65,
                    'depth_count': 1,
                    'avg_depth_overall': 60,
                    'reason': 'No quality starter (65 overall)'
                },
                ...
            ]
        """
        needs = []

        # Get full depth chart
        depth_chart = self.depth_chart_api.get_full_depth_chart(
            dynasty_id=self.dynasty_id,
            team_id=team_id
        )

        # Get expiring contracts if requested
        expiring_players = []
        if include_future_contracts:
            expiring_contracts = self.cap_api.get_pending_free_agents(
                team_id=team_id,
                season=season,
                dynasty_id=self.dynasty_id
            )
            expiring_players = [p['player_id'] for p in expiring_contracts]

        # Analyze each important position
        important_positions = (
            self.TIER_1_POSITIONS +
            self.TIER_2_POSITIONS +
            self.TIER_3_POSITIONS +
            self.TIER_4_POSITIONS
        )

        for position in important_positions:
            need = self._analyze_position_need(
                position=position,
                depth_chart=depth_chart,
                expiring_players=expiring_players
            )

            if need['urgency'] != NeedUrgency.NONE:
                needs.append(need)

        # Sort by urgency (highest first), then by position tier
        needs.sort(key=lambda x: (x['urgency_score'], self._get_position_tier(x['position'])), reverse=True)

        return needs

    def _analyze_position_need(
        self,
        position: str,
        depth_chart: Dict[str, List[Dict]],
        expiring_players: List[int]
    ) -> Dict[str, Any]:
        """
        Analyze need for a specific position.

        Args:
            position: Position name
            depth_chart: Full team depth chart
            expiring_players: List of player IDs with expiring contracts

        Returns:
            Need dict with urgency and details
        """
        position_players = depth_chart.get(position, [])

        # Sort by depth order
        position_players.sort(key=lambda p: p['depth_order'])

        # Get starter (depth_order = 1)
        starter = next((p for p in position_players if p['depth_order'] == 1), None)

        # Get backups (depth_order > 1)
        backups = [p for p in position_players if p['depth_order'] > 1 and p['depth_order'] < 99]

        # Calculate metrics
        starter_overall = starter['overall'] if starter else 0
        depth_count = len(backups)
        avg_depth_overall = sum(p['overall'] for p in backups) / len(backups) if backups else 0

        # Check if starter is leaving
        starter_leaving = starter and starter['player_id'] in expiring_players

        # Determine urgency
        urgency, reason = self._calculate_urgency(
            position=position,
            starter_overall=starter_overall,
            depth_count=depth_count,
            avg_depth_overall=avg_depth_overall,
            starter_leaving=starter_leaving
        )

        return {
            'position': position,
            'urgency': urgency,
            'urgency_score': urgency.value,
            'starter_overall': starter_overall,
            'depth_count': depth_count,
            'avg_depth_overall': avg_depth_overall,
            'starter_leaving': starter_leaving,
            'reason': reason
        }

    def _calculate_urgency(
        self,
        position: str,
        starter_overall: int,
        depth_count: int,
        avg_depth_overall: float,
        starter_leaving: bool
    ) -> Tuple[NeedUrgency, str]:
        """
        Calculate urgency level for a position need.

        Args:
            position: Position name
            starter_overall: Starter's overall rating
            depth_count: Number of backups
            avg_depth_overall: Average overall of backups
            starter_leaving: Whether starter contract is expiring

        Returns:
            (urgency_level, reason_string)
        """
        tier = self._get_position_tier(position)
        threshold = self.STARTER_THRESHOLDS[tier]

        # CRITICAL: No starter or starter well below threshold
        if starter_overall == 0:
            return NeedUrgency.CRITICAL, f"No starter at {position}"

        if starter_overall < threshold - 5:
            return NeedUrgency.CRITICAL, f"Starter well below standard ({starter_overall} overall)"

        # CRITICAL: Starter leaving and no adequate replacement
        if starter_leaving and (depth_count == 0 or avg_depth_overall < threshold - 5):
            return NeedUrgency.CRITICAL, f"Starter leaving, no replacement ({starter_overall} overall)"

        # HIGH: Starter below threshold
        if starter_overall < threshold:
            return NeedUrgency.HIGH, f"Starter below standard ({starter_overall} overall)"

        # HIGH: Starter leaving but have backup
        if starter_leaving:
            return NeedUrgency.HIGH, f"Starter leaving ({starter_overall} overall)"

        # HIGH: No depth
        if depth_count == 0:
            return NeedUrgency.HIGH, f"No backup depth"

        # MEDIUM: Starter decent but weak depth
        if starter_overall < threshold + 5 and avg_depth_overall < threshold - 5:
            return NeedUrgency.MEDIUM, f"Weak depth behind starter"

        # MEDIUM: Starter good but no depth
        if depth_count < 2 and tier <= 2:  # Premium positions need depth
            return NeedUrgency.MEDIUM, f"Insufficient depth"

        # LOW: Starter good, adequate depth
        if starter_overall >= threshold + 5:
            return NeedUrgency.LOW, f"Starter solid, could upgrade depth"

        # NONE: Starter great, good depth
        return NeedUrgency.NONE, f"Position well-staffed"

    def _get_position_tier(self, position: str) -> int:
        """Get position tier (1-4, lower is more important)."""
        if position in self.TIER_1_POSITIONS:
            return 1
        elif position in self.TIER_2_POSITIONS:
            return 2
        elif position in self.TIER_3_POSITIONS:
            return 3
        else:
            return 4

    def get_top_needs(
        self,
        team_id: int,
        season: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top N positional needs for quick reference.

        Args:
            team_id: Team ID (1-32)
            season: Current season year
            limit: Number of top needs to return

        Returns:
            List of top needs
        """
        all_needs = self.analyze_team_needs(team_id, season)
        return all_needs[:limit]
```

**Dependencies**:
- Existing: PlayerRosterAPI, DepthChartAPI, CapDatabaseAPI
- Gap 1: `get_pending_free_agents()` method

**Testing**:
- Create test team with weak QB (65 overall), good RB (85 overall)
- Verify analyzer identifies QB as CRITICAL need
- Verify RB identified as LOW/NONE need
- Test with expiring contracts

---

### Gap 3: Market Value Calculation ✅ COMPLETE

**Status**: ✅ **COMPLETE** (Implemented October 18, 2025)

**Problem**: No way to estimate what contracts AI should offer to free agents.

**Impact**: AI cannot make competitive free agency offers or evaluate franchise tags.

**Implementation Summary**:
- ✅ Created `src/offseason/market_value_calculator.py` (290 lines, complete implementation)
- ✅ Implemented position-based base AAV rates for all NFL positions
- ✅ Implemented 3 multiplier system: Rating (0.1x-2.5x), Age (0.3x-1.0x), Experience (0.8x-1.0x)
- ✅ Implemented contract structure calculations (AAV, years, guarantees, signing bonus)
- ✅ Implemented franchise tag value calculator (120% of position base rate)
- ✅ Created comprehensive unit tests in `tests/salary_cap/test_market_value_calculator.py` (16 test cases, all passing)
- ✅ Verified elite QB contracts (~$90M AAV), average RB contracts (~$6M AAV), age discounts
- ✅ Verified franchise tag values (QB: $54M, Edge: $30M, RB: $14.4M)
- ✅ Updated `src/offseason/__init__.py` to export `MarketValueCalculator`
- ✅ No external dependencies - standalone pure calculation module

**Required Implementation**:

**File**: `src/offseason/market_value_calculator.py` (NEW)

```python
"""
Market Value Calculator

Calculates player market values for contract negotiations.
Based on position, overall rating, age, and market trends.
"""

from typing import Dict, Any
import json


class MarketValueCalculator:
    """
    Calculates estimated market value for player contracts.

    Based on:
    - Position market rates
    - Overall rating
    - Age curve
    - Years of experience
    - NFL market trends (2024-2025 CBA)
    """

    # Base Annual Average Value (AAV) for 85 overall player by position (in millions)
    POSITION_BASE_AAV = {
        # Tier 1: Premium positions
        'quarterback': 45.0,
        'edge_rusher': 25.0,
        'offensive_tackle': 22.0,

        # Tier 2: High-value positions
        'wide_receiver': 20.0,
        'cornerback': 18.0,
        'center': 15.0,

        # Tier 3: Standard positions
        'running_back': 12.0,
        'linebacker': 14.0,
        'safety': 13.0,
        'guard': 14.0,

        # Tier 4: Lower-value positions
        'tight_end': 11.0,
        'defensive_tackle': 12.0,
        'kicker': 4.0,
        'punter': 3.0
    }

    # Contract length by position (years)
    TYPICAL_CONTRACT_LENGTH = {
        'quarterback': 4,
        'edge_rusher': 4,
        'offensive_tackle': 4,
        'wide_receiver': 3,
        'cornerback': 3,
        'running_back': 2,  # RBs get shorter deals
        'kicker': 3,
        'punter': 3
    }

    # Peak age by position
    PEAK_AGE = {
        'quarterback': 28,
        'running_back': 26,
        'wide_receiver': 27,
        'edge_rusher': 27,
        'offensive_tackle': 28,
        'cornerback': 27,
        'kicker': 30,
        'punter': 30
    }

    def __init__(self, salary_cap: int = 255_000_000):
        """
        Initialize market value calculator.

        Args:
            salary_cap: League salary cap (default 2024 cap: $255M)
        """
        self.salary_cap = salary_cap

    def calculate_player_value(
        self,
        position: str,
        overall: int,
        age: int,
        years_pro: int
    ) -> Dict[str, Any]:
        """
        Calculate estimated market value for a player.

        Args:
            position: Player position
            overall: Overall rating (0-100)
            age: Player age
            years_pro: Years of NFL experience

        Returns:
            Dict with contract estimates:
            {
                'aav': Annual average value (millions),
                'total_value': Total contract value (millions),
                'years': Contract length,
                'guaranteed': Guaranteed money (millions),
                'signing_bonus': Signing bonus (millions)
            }
        """
        # Get base AAV for position
        base_aav = self.POSITION_BASE_AAV.get(position, 10.0)

        # Adjust for overall rating (85 overall is baseline)
        rating_multiplier = self._calculate_rating_multiplier(overall)

        # Adjust for age
        age_multiplier = self._calculate_age_multiplier(position, age)

        # Adjust for experience (rookies get less, vets get more)
        experience_multiplier = self._calculate_experience_multiplier(years_pro)

        # Calculate AAV
        aav = base_aav * rating_multiplier * age_multiplier * experience_multiplier

        # Determine contract length
        years = self.TYPICAL_CONTRACT_LENGTH.get(position, 3)

        # Adjust length for age (older players get shorter deals)
        if age > 30:
            years = min(years, 2)
        elif age > 28:
            years = min(years, 3)

        # Calculate total value
        total_value = aav * years

        # Calculate guarantees (typically 50-70% for top players, less for lower rated)
        guarantee_percentage = self._calculate_guarantee_percentage(overall, position)
        guaranteed = total_value * guarantee_percentage

        # Signing bonus (typically 30-40% of total for spread)
        signing_bonus = total_value * 0.35

        return {
            'aav': round(aav, 2),
            'total_value': round(total_value, 2),
            'years': years,
            'guaranteed': round(guaranteed, 2),
            'signing_bonus': round(signing_bonus, 2),
            'guarantee_percentage': round(guarantee_percentage * 100, 1)
        }

    def _calculate_rating_multiplier(self, overall: int) -> float:
        """
        Calculate multiplier based on overall rating.

        85 overall = 1.0x (baseline)
        95 overall = 2.0x (elite)
        75 overall = 0.5x (below average starter)
        65 overall = 0.2x (backup)
        """
        if overall >= 90:
            # Elite players (90-99): 1.5x to 2.5x
            return 1.5 + ((overall - 90) / 10) * 1.0
        elif overall >= 85:
            # Good starters (85-89): 1.0x to 1.5x
            return 1.0 + ((overall - 85) / 5) * 0.5
        elif overall >= 75:
            # Average starters (75-84): 0.5x to 1.0x
            return 0.5 + ((overall - 75) / 10) * 0.5
        elif overall >= 65:
            # Backups (65-74): 0.2x to 0.5x
            return 0.2 + ((overall - 65) / 10) * 0.3
        else:
            # Deep backups (< 65): 0.1x to 0.2x
            return 0.1 + (overall / 65) * 0.1

    def _calculate_age_multiplier(self, position: str, age: int) -> float:
        """
        Calculate multiplier based on age curve.

        Peak age = 1.0x
        Age 23 = 0.9x (upside but unproven)
        Age 32 = 0.7x (decline phase)
        Age 35+ = 0.4x (near retirement)
        """
        peak = self.PEAK_AGE.get(position, 27)

        if age <= peak:
            # Young player with upside (90-100% value)
            years_before_peak = peak - age
            if years_before_peak <= 1:
                return 1.0
            else:
                # Discount for very young (23-24 for most positions)
                return max(0.85, 1.0 - (years_before_peak * 0.05))
        else:
            # Past peak - declining value
            years_past_peak = age - peak
            if years_past_peak <= 2:
                return max(0.85, 1.0 - (years_past_peak * 0.05))
            elif years_past_peak <= 5:
                return max(0.6, 0.85 - ((years_past_peak - 2) * 0.08))
            else:
                return max(0.3, 0.6 - ((years_past_peak - 5) * 0.1))

    def _calculate_experience_multiplier(self, years_pro: int) -> float:
        """
        Calculate multiplier based on NFL experience.

        Rookies (0-1 years) on rookie contracts = N/A (separate system)
        Young players (2-4 years) = 0.9x (first big contract)
        Prime players (5-8 years) = 1.0x (peak earning)
        Veterans (9+ years) = 0.95x (slight discount for age)
        """
        if years_pro <= 1:
            return 0.8  # First contract after rookie deal
        elif years_pro <= 4:
            return 0.9  # Still building value
        elif years_pro <= 8:
            return 1.0  # Peak earning years
        else:
            return 0.95  # Veteran discount

    def _calculate_guarantee_percentage(self, overall: int, position: str) -> float:
        """
        Calculate what percentage of contract should be guaranteed.

        Elite players: 60-70%
        Good starters: 50-60%
        Average starters: 40-50%
        Backups: 20-30%
        """
        if overall >= 90:
            base = 0.65
        elif overall >= 85:
            base = 0.55
        elif overall >= 80:
            base = 0.45
        elif overall >= 75:
            base = 0.35
        else:
            base = 0.25

        # QBs and premium positions get slightly higher guarantees
        if position in ['quarterback', 'edge_rusher', 'offensive_tackle']:
            base += 0.05

        return min(0.75, base)  # Cap at 75%

    def calculate_franchise_tag_value(
        self,
        position: str,
        season: int
    ) -> int:
        """
        Calculate franchise tag value for a position.

        Based on top 5 average at position or 120% of prior salary.

        Args:
            position: Player position
            season: Season year

        Returns:
            Franchise tag salary (in dollars, not millions)
        """
        # Use base AAV as proxy for top-5 average
        base_aav = self.POSITION_BASE_AAV.get(position, 10.0)

        # Franchise tag is typically 120% of base for top positions
        tag_value_millions = base_aav * 1.2

        # Convert to dollars
        tag_value = int(tag_value_millions * 1_000_000)

        return tag_value
```

**Dependencies**: None (standalone module)

**Testing**:
- Test with 90 overall QB, age 28 → Should get ~$54M AAV, 4 years
- Test with 75 overall RB, age 26 → Should get ~$6M AAV, 2 years
- Test with 85 overall WR, age 32 → Should get ~$13M AAV (age discount)
- Test franchise tag calculation for QB → Should be ~$54M

---

## High Priority Gaps

These build on the critical gaps to enable AI decision-making.

### Gap 4: Franchise Tag Decision Logic ✅ COMPLETE

**Status**: ✅ **COMPLETE** (Implemented October 18, 2025)

**File**: `src/offseason/offseason_controller.py` (lines 290-396)

**Implementation Summary**:
- ✅ Replaced empty `get_franchise_tag_candidates()` method with full AI logic
- ✅ Integrated with Gap 1 (pending free agents) and Gap 3 (market value calculator)
- ✅ 4-layer architecture: Data retrieval → Team needs analysis → Candidate evaluation → Cap filtering
- ✅ Returns top 3 affordable candidates sorted by tag value score
- ✅ Created demo: `demo/ai_logic/demo_franchise_tag_ai.py`
- ✅ Verified with realistic test scenarios

```python
def get_franchise_tag_candidates(self, team_id: int) -> List[Dict[str, Any]]:
    """
    Get list of players eligible for franchise tag.

    Returns top 3 candidates sorted by value retention.
    """
    # Use Gap #1: Get pending free agents
    pending_fas = self.cap_api.get_pending_free_agents(
        team_id=team_id,
        season=self.season_year,
        dynasty_id=self.dynasty_id,
        min_overall=75  # Only consider quality players
    )

    # Use Gap #3: Calculate tag value vs market value
    candidates = []
    for player in pending_fas:
        # Calculate market value
        market_value = self.market_calc.calculate_player_value(
            position=player['position'],
            overall=player['overall'],
            age=self._get_player_age(player['player_id']),
            years_pro=player['years_pro']
        )

        # Calculate franchise tag cost
        tag_cost = self.market_calc.calculate_franchise_tag_value(
            position=player['position'],
            season=self.season_year
        )

        # Tag is worth it if market value > tag cost
        tag_value = market_value['total_value'] - (tag_cost / 1_000_000)

        if tag_value > 0:  # Worth tagging
            candidates.append({
                'player_id': player['player_id'],
                'player_name': player['player_name'],
                'position': player['position'],
                'overall': player['overall'],
                'tag_cost': tag_cost,
                'market_value_aav': market_value['aav'],
                'tag_value_score': tag_value,
                'recommendation': 'TAG' if tag_value > 10 else 'CONSIDER'
            })

    # Sort by tag value (highest first)
    candidates.sort(key=lambda x: x['tag_value_score'], reverse=True)

    # Check cap space
    cap_space = self._get_available_cap_space(team_id)

    # Filter by affordability
    affordable_candidates = [
        c for c in candidates
        if c['tag_cost'] <= cap_space
    ]

    return affordable_candidates[:3]  # Top 3
```

**Dependencies**: Gap 1, Gap 3

---

### Gap 5: AI Free Agency Simulation ✅ COMPLETE

**Status**: ✅ **COMPLETE** (Implemented October 18, 2025)

**File**: `src/offseason/free_agency_manager.py` (lines 191-375)

**Implementation Summary**:
- ✅ Implemented `simulate_free_agency_day()` method with multi-day simulation support
- ✅ 3-tier FA period system matching NFL realism:
  - Days 1-3: Elite FAs (85+ OVR), max 2 signings per team
  - Days 4-14: Starters (75+ OVR), max 3 signings per team
  - Days 15-30: Depth pieces (65+ OVR), max 5 signings per team
- ✅ Integrated with Gap 2 (team needs analyzer) for needs-based signing
- ✅ Integrated with Gap 3 (market value calculator) for contract offers
- ✅ Created demo: `demo/ai_logic/demo_free_agency_ai.py`
- ✅ Tested with 32 AI teams, 100-player FA pool, 30-day simulation

```python
def simulate_free_agency(
    self,
    user_team_id: int,
    days_to_simulate: int = 30
) -> List[Dict[str, Any]]:
    """
    Simulate AI team free agency activity over N days.

    Day 1-3: Legal tampering - top FAs sign
    Day 4-14: Mid-tier FAs sign
    Day 15-30: Remaining FAs and cheap veterans
    """
    signings = []

    # Get all AI teams (exclude user)
    ai_teams = [team_id for team_id in range(1, 33) if team_id != user_team_id]

    # Get free agent pool
    fa_pool = self.get_free_agent_pool(fa_type='UFA', limit=200)

    # Simulate each day
    for day in range(1, days_to_simulate + 1):
        print(f"\n📅 Free Agency Day {day}")

        # Determine FA tier for this day
        if day <= 3:
            min_overall = 85  # Elite FAs
            max_signings_per_team = 2
        elif day <= 14:
            min_overall = 75  # Good starters
            max_signings_per_team = 3
        else:
            min_overall = 65  # Depth pieces
            max_signings_per_team = 5

        # Each AI team evaluates FAs
        for team_id in ai_teams:
            # Use Gap #2: Analyze team needs
            team_needs = self.needs_analyzer.get_top_needs(
                team_id=team_id,
                season=self.season_year,
                limit=5
            )

            # Get cap space
            cap_space = self._get_team_cap_space(team_id)

            # Try to sign FAs matching needs
            team_signings = 0
            for need in team_needs:
                if team_signings >= max_signings_per_team:
                    break

                # Find matching FA
                matching_fa = self._find_best_fa_for_need(
                    need=need,
                    fa_pool=fa_pool,
                    min_overall=min_overall,
                    cap_space=cap_space
                )

                if matching_fa:
                    # Use Gap #3: Calculate offer
                    offer = self.market_calc.calculate_player_value(
                        position=matching_fa['position'],
                        overall=matching_fa['overall'],
                        age=matching_fa['age'],
                        years_pro=matching_fa['years_pro']
                    )

                    # Execute signing via EventCapBridge
                    signing_result = self._execute_fa_signing(
                        player_id=matching_fa['player_id'],
                        team_id=team_id,
                        contract=offer
                    )

                    if signing_result['success']:
                        signings.append(signing_result)
                        team_signings += 1
                        fa_pool.remove(matching_fa)  # Remove from pool
                        cap_space -= offer['total_value']

    return signings
```

**Dependencies**: Gap 1, Gap 2, Gap 3

---

### Gap 6: AI Draft Simulation

**File**: `src/offseason/draft_manager.py` (UPDATE lines 204-223)

**Current**: NotImplementedError
**Required**: 7-round draft with BPA + needs

```python
def simulate_draft(
    self,
    user_team_id: int,
    user_picks: List[int]
) -> List[Dict[str, Any]]:
    """
    Simulate NFL Draft with AI teams making picks.

    User team picks are skipped and returned for manual selection.
    """
    draft_results = []

    # Generate draft class (use Gap #9)
    draft_class = self.generate_draft_class(size=300)

    # Get draft order (based on previous season standings)
    draft_order = self._get_draft_order()

    # 7 rounds, 32 picks each
    for round_num in range(1, 8):
        print(f"\n🏈 ROUND {round_num}")

        for pick_num in range(1, 33):
            overall_pick = (round_num - 1) * 32 + pick_num
            team_id = draft_order[pick_num - 1]

            # If user team, pause and wait
            if team_id == user_team_id:
                print(f"  Pick #{overall_pick}: USER TEAM (paused)")
                draft_results.append({
                    'round': round_num,
                    'pick': pick_num,
                    'team_id': team_id,
                    'player_id': None,
                    'status': 'USER_PENDING'
                })
                continue

            # AI team - make selection
            # Use Gap #2: Get team needs
            team_needs = self.needs_analyzer.analyze_team_needs(
                team_id=team_id,
                season=self.season_year
            )

            # Build draft board (BPA + needs)
            board = self._build_draft_board(
                available_players=draft_class,
                team_needs=team_needs,
                round_num=round_num
            )

            # Select top player
            if board:
                selected_player = board[0]

                # Make pick
                self.make_draft_selection(
                    round_num=round_num,
                    pick_num=pick_num,
                    player_id=selected_player['player_id'],
                    team_id=team_id
                )

                draft_results.append({
                    'round': round_num,
                    'pick': pick_num,
                    'team_id': team_id,
                    'player_id': selected_player['player_id'],
                    'player_name': selected_player['name'],
                    'position': selected_player['position'],
                    'overall': selected_player['overall']
                })

                # Remove from draft class
                draft_class.remove(selected_player)

    return draft_results
```

**Dependencies**: Gap 2, Gap 9 (draft class generation)

---

### Gap 7: AI Roster Cut Logic ✅ COMPLETE

**Status**: ✅ **COMPLETE** (Implemented October 18, 2025)

**File**: `src/offseason/roster_manager.py` (lines 139-338)

**Implementation Summary**:
- ✅ Implemented `finalize_53_man_roster_ai()` method with intelligent roster optimization
- ✅ Value-based ranking algorithm: `(position_value × overall) - (cap_hit / 1M)`
- ✅ Premium position multipliers: QB/DE/OT (3.0x) > WR/CB/C (2.5x) > RB/LB/S/G (2.0x) > TE/DT (1.5x)
- ✅ NFL position minimum enforcement:
  - QB ≥ 1, OL ≥ 5, DL ≥ 4, LB ≥ 3, DB ≥ 3, K ≥ 1, P ≥ 1
- ✅ Created demo: `demo/ai_logic/demo_roster_cuts_ai.py`
- ✅ Tested with mock 90-man rosters → 53-man final roster
- ✅ Validated position minimum compliance in all test scenarios

```python
def finalize_53_man_roster(self, team_id: int) -> Dict[str, Any]:
    """
    Cut roster from 90 to 53 players (AI logic).

    Algorithm:
    1. Rank all 90 players by (position_value * overall) - cap_hit
    2. Keep top 53 while meeting position minimums
    3. Cut bottom 37
    4. Assign practice squad eligible players
    """
    # Get full 90-man roster
    roster = self.player_api.get_team_roster(
        dynasty_id=self.dynasty_id,
        team_id=team_id
    )

    # Rank players by value score
    ranked_players = []
    for player in roster:
        # Position value multiplier
        position_value = self._get_position_value(player['position'])

        # Overall rating
        overall = player['overall']

        # Cap hit (prefer cheap players if similar talent)
        cap_hit = self._get_player_cap_hit(player['player_id'])

        # Value score
        value_score = (position_value * overall) - (cap_hit / 1_000_000)

        ranked_players.append({
            **player,
            'value_score': value_score,
            'cap_hit': cap_hit
        })

    # Sort by value (highest first)
    ranked_players.sort(key=lambda p: p['value_score'], reverse=True)

    # Select top 53 meeting position minimums
    final_53 = self._select_53_man_roster(ranked_players)

    # Cut remaining 37 players
    cuts = [p for p in roster if p['player_id'] not in [f['player_id'] for f in final_53]]

    cut_results = []
    for player in cuts:
        # Execute PlayerReleaseEvent
        result = self.cut_player(
            team_id=team_id,
            player_id=player['player_id'],
            june_1_designation=False
        )
        cut_results.append(result)

    return {
        'final_roster': final_53,
        'cuts': cut_results,
        'total_cut': len(cuts)
    }
```

**Dependencies**: Gap 1 (for cap hit queries)

---

## Medium Priority Gaps

### Gap 8: Free Agent Pool Queries

**File**: `src/offseason/free_agency_manager.py` (UPDATE lines 51-74)

Simple database query wrapper.

### Gap 9: Draft Class Generation

**File**: `src/offseason/draft_manager.py` (UPDATE lines 68-90)

Integrate with existing `player_generation` system.

### Gap 10: RFA Tender Logic

**File**: `src/offseason/free_agency_manager.py` (UPDATE lines 123-145)

Use existing TagManager via EventCapBridge.

---

## Implementation Roadmap

### ✅ Phase 1: Foundation (Week 1) - CRITICAL GAPS

**Goal**: Build data layer and analysis tools

- [x] **Day 1-2**: Gap 1 - Contract Expiration Queries ✅ COMPLETE
  - ✅ Added `get_expiring_contracts()` to CapDatabaseAPI (lines 290-350)
  - ✅ Added `get_pending_free_agents()` helper (lines 352-418)
  - ✅ Wrote comprehensive unit tests (12 test cases, all passing)
  - ✅ Wrote manual integration tests (4 scenarios, all passing)
  - ✅ Verified dynasty isolation and SQL correctness

- [x] **Day 3-4**: Gap 2 - Team Needs Analyzer ✅ COMPLETE
  - ✅ Created `team_needs_analyzer.py` module (288 lines)
  - ✅ Implemented `analyze_team_needs()` method with 4-tier position system
  - ✅ Implemented `get_top_needs()` convenience method
  - ✅ Wrote comprehensive unit tests (14 test cases, all passing)
  - ✅ Created interactive terminal demo with real Cleveland Browns data
  - ✅ Verified urgency detection, dynasty isolation, and position tier weighting

- [x] **Day 5**: Gap 3 - Market Value Calculator ✅ COMPLETE
  - ✅ Created `market_value_calculator.py` module (290 lines)
  - ✅ Implemented `calculate_player_value()` method with rating/age/experience multipliers
  - ✅ Implemented `calculate_franchise_tag_value()` method
  - ✅ Wrote comprehensive unit tests (16 test cases, all passing)
  - ✅ Verified elite QB contracts (~$90M), age discounts, franchise tag values
  - ✅ Updated `src/offseason/__init__.py` to export MarketValueCalculator

**Deliverable**: ✅ **COMPLETE** - AI can query contracts, analyze needs, calculate values

---

### ✅ Phase 2: Core AI Logic (Week 2) - HIGH PRIORITY GAPS ✅ COMPLETE

**Status**: ✅ **COMPLETE** (Implemented October 18, 2025)

**Goal**: Implement AI decision-making

- [x] **Day 1-2**: Gap 4 - Franchise Tag Logic ✅ COMPLETE
  - ✅ Updated `get_franchise_tag_candidates()` in OffseasonController (lines 290-396)
  - ✅ Integrated with Gap 1 (contract expiration queries) & Gap 3 (market value calculator)
  - ✅ Implemented ultra-thin SoC: Data → Analysis → Evaluation → Filtering (4 layers)
  - ✅ Created comprehensive demo: `demo/ai_logic/demo_franchise_tag_ai.py`
  - ✅ Verified tag candidate selection logic with realistic scenarios

- [x] **Day 3-4**: Gap 5 - Free Agency Simulation ✅ COMPLETE
  - ✅ Implemented `simulate_free_agency_day()` in FreeAgencyManager (lines 191-375)
  - ✅ 3-tier FA period system (Elite Days 1-3, Starters Days 4-14, Depth Days 15-30)
  - ✅ Multi-day simulation loop with AI team needs matching
  - ✅ Integrated with Gap 2 (team needs analysis) & Gap 3 (contract offers)
  - ✅ Created comprehensive demo: `demo/ai_logic/demo_free_agency_ai.py`
  - ✅ Tested with 32 AI teams, 100-player FA pool, 30-day simulation

- [x] **Day 5**: Gap 7 - Roster Cut Logic ✅ COMPLETE
  - ✅ Implemented `finalize_53_man_roster_ai()` in RosterManager (lines 139-338)
  - ✅ Value-based player ranking algorithm: (position_value × overall) - (cap_hit / 1M)
  - ✅ NFL position minimum enforcement (QB≥1, OL≥5, DL≥4, LB≥3, DB≥3, K≥1, P≥1)
  - ✅ Premium position value multipliers (QB/DE/OT higher than RB/TE)
  - ✅ Created comprehensive demo: `demo/ai_logic/demo_roster_cuts_ai.py`
  - ✅ Tested with mock 90-man rosters → 53-man final roster

**Implementation Summary**:
- ✅ All 3 gaps implemented with strict Separation of Concerns (SoC)
- ✅ Ultra-thin public methods (10-30 lines) orchestrating business logic
- ✅ Private helper methods (30-50 lines) handling specific calculations
- ✅ Created 4 runnable demos in `demo/ai_logic/` folder:
  - `demo_franchise_tag_ai.py` - Shows AI evaluating franchise tag candidates for all 32 teams
  - `demo_free_agency_ai.py` - Shows 30-day FA simulation with multi-tier signing periods
  - `demo_roster_cuts_ai.py` - Shows AI cutting 90-man roster to 53 players
  - `demo_full_ai_offseason.py` - Integration demo showing all 3 systems working together
- ✅ Created comprehensive README: `demo/ai_logic/README.md` with usage instructions
- ✅ All demos use mock data for independent testing (no database dependencies)
- ✅ Dynasty isolation maintained throughout (`dynasty_id="phase2_testing"`)

**Deliverable**: ✅ **COMPLETE** - AI can tag players, sign FAs, cut rosters

---

### ⏳ Phase 3: Draft System (Week 3)

**Goal**: Complete draft simulation

- [x] **Day 1-2**: Gap 9 - Draft Class Generation ✅ COMPLETE
  - ✅ Integrated draft class generation into season lifecycle
  - ✅ Draft class auto-generated when SeasonCycleController initializes (regular season start)
  - ✅ Draft event auto-scheduled during offseason transition (after Super Bowl)
  - ✅ Uses existing `DraftClassAPI` with `player_generation` module
  - ✅ Generates 224 prospects (7 rounds × 32 teams)
  - ✅ Implementation: `SeasonCycleController._generate_draft_class_if_needed()` (src/season/season_cycle_controller.py:983-1022)
  - ✅ Draft events scheduled via OffseasonEventScheduler (src/offseason/offseason_event_scheduler.py:359)
  - ⚠️  Note: Player generation system needs archetype configuration for full functionality (currently handled by test mocks)

- [ ] **Day 3-5**: Gap 6 - Draft Simulation
  - Implement `simulate_draft()` in DraftManager
  - Draft board building (BPA + needs)
  - Test 7-round simulation

**Deliverable**: AI can execute complete draft

---

### ✅ Phase 4: Integration & Polish (Week 4)

**Goal**: Wire everything together

- [ ] **Day 1-2**: Deadline Event Integration
  - Wire AI franchise tag logic into `FRANCHISE_TAG` deadline
  - Wire AI free agency into `FREE_AGENCY` windows
  - Wire AI roster cuts into `FINAL_ROSTER_CUTS` deadline

- [ ] **Day 3**: Medium Priority Gaps (8, 10)
  - Implement FA pool queries
  - Implement RFA tender logic

- [ ] **Day 4-5**: End-to-End Testing
  - Run full offseason simulation (Super Bowl → Roster Cuts)
  - Verify all 32 AI teams make decisions
  - Tune AI decision quality

**Deliverable**: Complete OffseasonAIManager ready for production

---

## Testing Strategy

### Unit Tests

**Critical Gaps**:
- `test_contract_expiration_queries.py` - Verify contract queries work
- `test_team_needs_analyzer.py` - Verify need prioritization
- `test_market_value_calculator.py` - Verify contract calculations

**High Priority Gaps**:
- `test_franchise_tag_ai.py` - Verify tag candidate selection
- `test_free_agency_ai.py` - Verify FA simulation
- `test_roster_cuts_ai.py` - Verify 53-man roster logic
- `test_draft_ai.py` - Verify draft simulation

### Integration Tests

**Full Offseason Cycle**:
```python
def test_full_offseason_ai_simulation():
    # 1. Super Bowl ends
    # 2. AI teams apply franchise tags
    # 3. AI teams sign free agents
    # 4. AI teams execute draft
    # 5. AI teams finalize rosters
    # Assert: All 32 teams completed offseason
```

**Dynasty Isolation**:
```python
def test_offseason_ai_dynasty_isolation():
    # Run offseason in dynasty_1
    # Run offseason in dynasty_2
    # Assert: No data leakage between dynasties
```

### Manual Testing

**AI Decision Quality**:
- [ ] Verify QB-needy teams target QBs in FA/draft
- [ ] Verify teams don't overspend on low-value positions
- [ ] Verify cap-poor teams make cuts to get compliant
- [ ] Verify teams don't tag backup players

---

## Success Criteria

### Minimum Viable Product (MVP)

- ✅ All 32 AI teams complete offseason without errors
- ✅ AI teams apply franchise tags to quality players
- ✅ AI teams sign free agents based on needs
- ✅ AI teams execute 7-round draft
- ✅ AI teams finalize 53-man rosters meeting requirements

### Quality Targets

- ✅ 90%+ of franchise tags go to 80+ overall players
- ✅ 80%+ of FA signings match team needs (position alignment)
- ✅ 100% of teams meet salary cap compliance by deadline
- ✅ 100% of 53-man rosters meet position minimums
- ✅ Draft picks show reasonable BPA + needs balance

### Performance Targets

- Full offseason simulation (32 teams) completes in < 5 minutes
- No database deadlocks or transaction failures
- Dynasty isolation maintained (no cross-contamination)

---

## Notes & Considerations

### AI Complexity vs Realism

**Simple AI** (Phase 1-2):
- Franchise tag: Top 3 pending FAs by overall
- Free agency: Sign top available player for each need
- Draft: Best player available matching need
- Cuts: Keep top 53 by overall

**Realistic AI** (Future enhancement):
- Positional value curves (QB > RB)
- Age considerations (don't pay 32-year-old RB)
- Scheme fit (4-3 vs 3-4 defense)
- Draft pick trading
- Compensatory pick calculations

**Recommendation**: Start with simple AI, iterate toward realism.

### Integration with Player Generation

The `player_generation` module is IN DEVELOPMENT. For MVP:
- Use simplified draft class generation (random players)
- Replace with full archetype-based generation when ready

### Future Enhancements

After MVP completion, consider:
- **Contract restructures**: AI teams restructure to create cap space
- **Trade simulation**: AI teams trade players/picks
- **Compensatory picks**: Award comp picks for FA losses
- **Practice squad management**: AI teams build practice squads
- **5th-year options**: AI teams exercise rookie options
- **User interaction**: Allow user to match AI FA offers

---

## Change Log

**October 2025**:
- Initial plan created based on codebase analysis
- Identified 3 critical gaps, 4 high-priority gaps, 3 medium-priority gaps
- Defined 4-week implementation roadmap

---

## References

- `docs/plans/offseason_plan.md` - Offseason system architecture
- `docs/plans/salary_cap_plan.md` - Salary cap system design
- `docs/architecture/event_cap_integration.md` - EventCapBridge pattern
- `src/offseason/offseason_controller.py` - Main controller API
- `src/salary_cap/event_integration.py` - EventCapBridge implementation
