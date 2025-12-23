"""
Player Popularity System Demo

Run with: python demos/popularity_demo.py

Demonstrates:
- 6 pre-scripted scenarios showing popularity dynamics
- Breakout stars, injury decline, trade journeys, MVP races
- Week-by-week progression with event timeline
- Component breakdown (Performance × Visibility × Market)
- Terminal output with Unicode box drawing (no external dependencies)

Scenarios:
  A. Breakout Star - Rookie QB rises from 45 to 82
  B. Injury Decline - Veteran RB drops during IR stint
  C. Trade Journey - WR navigates market transition
  D. MVP Candidate - QB reaches transcendent tier
  E. Playoff Hero - Backup becomes legend overnight
  F. Small Market Ceiling - Elite LB hits visibility cap
"""

import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

# Box drawing characters for clean output
BOX_TL = "┌"
BOX_TR = "┐"
BOX_BL = "└"
BOX_BR = "┘"
BOX_H = "─"
BOX_V = "│"
BOX_ML = "├"
BOX_MR = "┤"

# Trend symbols
TREND_RISING = "↑"
TREND_FALLING = "↓"
TREND_STABLE = "→"
STAR = "⭐"
FIRE = "🔥"


class PopularityTier(Enum):
    """Player popularity tiers."""
    TRANSCENDENT = "TRANSCENDENT"  # 90-100
    STAR = "STAR"                  # 75-89
    KNOWN = "KNOWN"                # 50-74
    ROLE_PLAYER = "ROLE_PLAYER"   # 25-49
    UNKNOWN = "UNKNOWN"            # 0-24


class TrendDirection(Enum):
    """Popularity trend direction."""
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"


@dataclass
class MockPlayer:
    """Mock player for demo scenarios.

    Popularity Formula:
        Base = (Performance × Visibility × Market) - Decay
        Final = clamp(Base + Bonuses, 0, 100)

    Components:
        - Performance (0-100): Overall rating, stats, grades
        - Visibility (0.5x-5.0x): Media exposure, awards, storylines
        - Market (0.8x-2.0x): Team market size multiplier
        - Decay (0-5): Weekly decay for inactive/injured players

    Tiers:
        - Transcendent: 90-100 (household names)
        - Star: 75-89 (nationally recognized)
        - Known: 50-74 (casually known)
        - Role Player: 25-49 (team/position fans know)
        - Unknown: 0-24 (rarely mentioned)
    """
    name: str
    position: str
    team: str
    team_id: int

    # Core components
    popularity: float
    performance_score: float  # Base performance (overall/stats)
    visibility_mult: float     # Media/storyline multiplier
    market_mult: float         # Team market size multiplier

    # Display metadata
    tier: PopularityTier
    trend: TrendDirection
    change: float
    history: List[float] = field(default_factory=list)
    events: List[str] = field(default_factory=list)

    # Week tracking
    current_week: int = 1

    def __post_init__(self):
        """Initialize history with starting popularity."""
        if not self.history:
            self.history = [self.popularity]

    def calculate_tier(self) -> PopularityTier:
        """Calculate tier based on popularity score."""
        if self.popularity >= 90:
            return PopularityTier.TRANSCENDENT
        elif self.popularity >= 75:
            return PopularityTier.STAR
        elif self.popularity >= 50:
            return PopularityTier.KNOWN
        elif self.popularity >= 25:
            return PopularityTier.ROLE_PLAYER
        else:
            return PopularityTier.UNKNOWN

    def calculate_trend(self) -> TrendDirection:
        """Calculate trend from last 4 weeks."""
        if len(self.history) < 2:
            return TrendDirection.STABLE

        recent = self.history[-4:]  # Last 4 weeks
        if len(recent) < 2:
            return TrendDirection.STABLE

        avg_change = (recent[-1] - recent[0]) / len(recent)

        if avg_change > 2:
            return TrendDirection.RISING
        elif avg_change < -2:
            return TrendDirection.FALLING
        else:
            return TrendDirection.STABLE

    def update_week(self, new_popularity: float, week: int):
        """Update player state for new week."""
        self.change = new_popularity - self.popularity
        self.popularity = new_popularity
        self.history.append(new_popularity)
        self.current_week = week
        self.tier = self.calculate_tier()
        self.trend = self.calculate_trend()


def create_scenario_players() -> List[MockPlayer]:
    """Create 6 test players with different storylines.

    Player A: Breakout Star (rookie QB, small market)
    Player B: Injury Decline (veteran RB, large market)
    Player C: Trade Journey (WR changing markets)
    Player D: MVP Candidate (QB, large market)
    Player E: Playoff Hero (backup QB to legend)
    Player F: Small Market Ceiling (elite LB)
    """
    return [
        # A: Breakout Star - Rookie QB (Jacksonville)
        MockPlayer(
            name="Player A (Trevor Lawrence)",
            position="QB",
            team="Jacksonville Jaguars",
            team_id=11,
            popularity=45.0,
            performance_score=80.0,
            visibility_mult=1.2,  # Rookie hype
            market_mult=0.9,      # Small market
            tier=PopularityTier.ROLE_PLAYER,
            trend=TrendDirection.STABLE,
            change=0.0,
        ),

        # B: Injury Decline - Veteran RB (Dallas)
        MockPlayer(
            name="Player B (Ezekiel Elliott)",
            position="RB",
            team="Dallas Cowboys",
            team_id=17,
            popularity=75.0,
            performance_score=82.0,
            visibility_mult=1.5,  # Established star
            market_mult=1.8,      # Large market (Dallas)
            tier=PopularityTier.STAR,
            trend=TrendDirection.STABLE,
            change=0.0,
        ),

        # C: Trade Journey - WR (Chicago → New York)
        MockPlayer(
            name="Player C (DJ Moore)",
            position="WR",
            team="Chicago Bears",
            team_id=21,
            popularity=70.0,
            performance_score=85.0,
            visibility_mult=1.3,
            market_mult=1.2,      # Medium market (Chicago)
            tier=PopularityTier.KNOWN,
            trend=TrendDirection.STABLE,
            change=0.0,
        ),

        # D: MVP Candidate - QB (Kansas City)
        MockPlayer(
            name="Player D (Patrick Mahomes)",
            position="QB",
            team="Kansas City Chiefs",
            team_id=14,
            popularity=80.0,
            performance_score=95.0,
            visibility_mult=1.8,  # Already high profile
            market_mult=1.5,      # Large market
            tier=PopularityTier.STAR,
            trend=TrendDirection.STABLE,
            change=0.0,
        ),

        # E: Playoff Hero - Backup QB (Philadelphia)
        MockPlayer(
            name="Player E (Nick Foles)",
            position="QB",
            team="Philadelphia Eagles",
            team_id=19,
            popularity=45.0,
            performance_score=72.0,
            visibility_mult=0.8,  # Career backup
            market_mult=1.6,      # Large market
            tier=PopularityTier.ROLE_PLAYER,
            trend=TrendDirection.STABLE,
            change=0.0,
        ),

        # F: Small Market Ceiling - Elite LB (Jacksonville)
        MockPlayer(
            name="Player F (Josh Allen)",
            position="LB",
            team="Jacksonville Jaguars",
            team_id=11,
            popularity=60.0,
            performance_score=90.0,
            visibility_mult=1.1,  # Defensive player, limited exposure
            market_mult=0.9,      # Small market
            tier=PopularityTier.KNOWN,
            trend=TrendDirection.STABLE,
            change=0.0,
        ),
    ]


def generate_events_for_week(week: int, scenario: str) -> Dict[str, List[Tuple[str, str]]]:
    """Generate events for specific week/scenario combinations.

    Returns:
        Dict mapping player name to list of (event_type, description) tuples

    Event Types (with emoji):
        BREAKOUT: ⚡ Major performance spike
        INJURY: 🏥 Injury/IR status
        TRADE: 🔄 Team change
        AWARD: 🏆 Award/recognition
        PLAYOFF: 🏈 Playoff performance
        COMEBACK: 💪 Return from injury
        HEADLINES: 📰 Media coverage
    """
    events = {}

    # Scenario A: Breakout Star
    if scenario in ['all', 'breakout']:
        if week == 5:
            events['Player A (Trevor Lawrence)'] = [
                ('BREAKOUT', '312 passing yards, 4 TDs vs Bengals'),
                ('HEADLINES', '+3 national headlines'),
                ('SOCIAL', '87 posts, 12K+ engagement'),
            ]
        elif week == 10:
            events['Player A (Trevor Lawrence)'] = [
                ('AWARD', 'Enters MVP race top 10'),
                ('HEADLINES', 'Featured on NFL Network'),
            ]

    # Scenario B: Injury Decline
    if scenario in ['all', 'injury']:
        if week == 3:
            events['Player B (Ezekiel Elliott)'] = [
                ('INJURY', 'Knee injury - Placed on IR'),
            ]
        elif week in [4, 5, 6, 7]:
            events['Player B (Ezekiel Elliott)'] = [
                ('INJURY', 'Still on IR (no games)'),
            ]
        elif week == 8:
            events['Player B (Ezekiel Elliott)'] = [
                ('COMEBACK', 'Activated from IR'),
                ('HEADLINES', 'Return storyline coverage'),
            ]

    # Scenario C: Trade Journey
    if scenario in ['all', 'trade']:
        if week == 5:
            events['Player C (DJ Moore)'] = [
                ('TRADE', 'Traded to New York Giants'),
                ('HEADLINES', 'Trade coverage (disruption)'),
            ]
        elif week == 6:
            events['Player C (DJ Moore)'] = [
                ('HEADLINES', 'Market transition (25% complete)'),
            ]
        elif week == 9:
            events['Player C (DJ Moore)'] = [
                ('HEADLINES', 'Full integration to NY market'),
            ]
        elif week == 12:
            events['Player C (DJ Moore)'] = [
                ('BREAKOUT', '140 receiving yards, 2 TDs in NY'),
            ]

    # Scenario D: MVP Candidate
    if scenario in ['all', 'mvp']:
        if week == 8:
            events['Player D (Patrick Mahomes)'] = [
                ('AWARD', 'Enters MVP race top 10'),
            ]
        elif week == 10:
            events['Player D (Patrick Mahomes)'] = [
                ('AWARD', 'Enters MVP race top 3'),
            ]
        elif week == 15:
            events['Player D (Patrick Mahomes)'] = [
                ('HEADLINES', 'Featured in 5 national headlines'),
            ]
        elif week == 18:
            events['Player D (Patrick Mahomes)'] = [
                ('AWARD', 'Wins MVP'),
            ]

    # Scenario E: Playoff Hero
    if scenario in ['all', 'playoff']:
        if week == 19:  # Wild Card
            events['Player E (Nick Foles)'] = [
                ('PLAYOFF', 'Starts due to injury, wins game'),
                ('HEADLINES', 'Cinderella story begins'),
            ]
        elif week == 20:  # Divisional
            events['Player E (Nick Foles)'] = [
                ('PLAYOFF', '250 yards, 2 TDs in divisional win'),
            ]
        elif week == 21:  # Conference
            events['Player E (Nick Foles)'] = [
                ('PLAYOFF', 'Game-winning drive in final 2 mins'),
                ('HEADLINES', 'National media frenzy'),
            ]
        elif week == 22:  # Super Bowl
            events['Player E (Nick Foles)'] = [
                ('AWARD', 'Super Bowl MVP'),
                ('HEADLINES', 'Legend overnight'),
            ]

    # Scenario F: Small Market Ceiling
    if scenario in ['all', 'ceiling']:
        if week == 8:
            events['Player F (Josh Allen)'] = [
                ('AWARD', 'DPOY race top 5'),
            ]
        elif week == 12:
            events['Player F (Josh Allen)'] = [
                ('AWARD', 'All-Pro selection'),
            ]
        elif week == 18:
            events['Player F (Josh Allen)'] = [
                ('AWARD', 'Wins DPOY'),
            ]

    return events


def calculate_mock_popularity(player: MockPlayer, events: List[Tuple[str, str]]) -> float:
    """Calculate new popularity based on events.

    Formula: Base = (Performance × Visibility × Market) - Decay

    Event Modifiers:
        BREAKOUT: +12 performance, +0.9 visibility
        INJURY: -3 decay per week
        TRADE: -20% immediate disruption, 4-week market transition
        AWARD (MVP race top 10): +0.3 visibility
        AWARD (MVP race top 3): +0.5 visibility
        AWARD (MVP/DPOY win): +20 immediate boost
        AWARD (All-Pro): +10 immediate boost
        PLAYOFF: +1.5x visibility multiplier
        COMEBACK: +5 immediate boost
    """
    # Extract event types
    event_types = [e[0] for e in events]

    # Start with current components
    perf = player.performance_score
    vis = player.visibility_mult
    market = player.market_mult
    decay = 0
    instant_bonus = 0

    # Apply event modifiers
    for event_type, event_desc in events:
        if event_type == 'BREAKOUT':
            perf += 12
            vis += 0.9

        elif event_type == 'INJURY':
            if 'Still on IR' in event_desc or 'Placed on IR' in event_desc:
                decay += 3

        elif event_type == 'TRADE':
            if 'Traded to' in event_desc:
                # Immediate 20% disruption
                instant_bonus -= player.popularity * 0.2
                # Start market transition (Chicago 1.2 → NY 1.7)
                player.market_mult = 1.2  # Will transition over 4 weeks
            elif 'Market transition (25% complete)' in event_desc:
                player.market_mult = 1.2 + (1.7 - 1.2) * 0.25
                market = player.market_mult
            elif 'Full integration' in event_desc:
                player.market_mult = 1.7
                market = player.market_mult

        elif event_type == 'AWARD':
            if 'MVP race top 10' in event_desc:
                vis += 0.3
            elif 'MVP race top 3' in event_desc:
                vis += 0.5
            elif 'Wins MVP' in event_desc:
                instant_bonus += 20
            elif 'Wins DPOY' in event_desc:
                instant_bonus += 15
            elif 'All-Pro' in event_desc:
                instant_bonus += 10
            elif 'DPOY race top 5' in event_desc:
                vis += 0.4

        elif event_type == 'PLAYOFF':
            if 'Super Bowl MVP' in event_desc:
                instant_bonus += 15
            else:
                vis *= 1.5  # Playoff multiplier
                instant_bonus += 8

        elif event_type == 'COMEBACK':
            instant_bonus += 5
            vis += 0.2

        elif event_type == 'HEADLINES':
            if '+3 national headlines' in event_desc:
                vis += 0.3
            elif 'Featured in 5 national headlines' in event_desc:
                vis += 0.5

    # Update player components
    player.performance_score = perf
    player.visibility_mult = vis

    # Calculate base popularity
    base_pop = (perf * vis * market) - decay + instant_bonus

    # Apply minor decay for no activity
    if not events:
        base_pop -= 1

    # Clamp to 0-100
    return max(0, min(100, base_pop))


def get_event_emoji(event_type: str) -> str:
    """Return emoji for event type."""
    emoji_map = {
        'BREAKOUT': '⚡',
        'INJURY': '🏥',
        'TRADE': '🔄',
        'AWARD': '🏆',
        'PLAYOFF': '🏈',
        'COMEBACK': '💪',
        'HEADLINES': '📰',
        'SOCIAL': '📱',
    }
    return emoji_map.get(event_type, '📰')


def get_trend_symbol(trend: TrendDirection) -> str:
    """Return symbol for trend."""
    if trend == TrendDirection.RISING:
        return TREND_RISING
    elif trend == TrendDirection.FALLING:
        return TREND_FALLING
    else:
        return TREND_STABLE


def print_header(title: str):
    """Print a section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def print_subheader(title: str):
    """Print a subsection header."""
    print()
    print(f"{BOX_H * 80}")
    print(f"  {title}")
    print(f"{BOX_H * 80}")
    print()


def print_formula_display():
    """Display the popularity formula."""
    width = 78

    print(f"{BOX_TL}{BOX_H * width}{BOX_TR}")
    print(f"{BOX_V} {'PLAYER POPULARITY SYSTEM FORMULA':<{width-1}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")
    print(f"{BOX_V}  {'Formula: Popularity = (Performance × Visibility × Market) - Decay':<{width-3}}{BOX_V}")
    print(f"{BOX_V}  {'Range: 0-100':<{width-3}}{BOX_V}")
    print(f"{BOX_V}{' ' * width}{BOX_V}")
    print(f"{BOX_V}  {'Tiers:':<{width-3}}{BOX_V}")
    print(f"{BOX_V}    {'⭐ Transcendent (90-100) - Household names':<{width-5}}{BOX_V}")
    print(f"{BOX_V}    {'✨ Star (75-89) - Nationally recognized':<{width-5}}{BOX_V}")
    print(f"{BOX_V}    {'✓ Known (50-74) - Casually known':<{width-5}}{BOX_V}")
    print(f"{BOX_V}    {'· Role Player (25-49) - Position fans know':<{width-5}}{BOX_V}")
    print(f"{BOX_V}    {'○ Unknown (0-24) - Rarely mentioned':<{width-5}}{BOX_V}")
    print(f"{BOX_BL}{BOX_H * width}{BOX_BR}")
    print()


def print_player_card(player: MockPlayer, week: int, use_color: bool = True):
    """Display single player card with box drawing."""
    width = 78

    print(f"{BOX_TL}{BOX_H * width}{BOX_TR}")

    # Header with player name
    header = f"{player.name} ({player.position}) - {player.team}"
    print(f"{BOX_V} {header:<{width-1}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")

    # Status row with tier and trend
    tier_symbol = {
        PopularityTier.TRANSCENDENT: "⭐",
        PopularityTier.STAR: "✨",
        PopularityTier.KNOWN: "✓",
        PopularityTier.ROLE_PLAYER: "·",
        PopularityTier.UNKNOWN: "○",
    }.get(player.tier, "·")

    trend_symbol = get_trend_symbol(player.trend)

    status = f"Week {week:<2} │ POP: {player.popularity:>5.1f} │ TIER: {tier_symbol} {player.tier.value:<15} │ TREND: {player.trend.value} {trend_symbol}"
    print(f"{BOX_V} {status:<{width-1}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * 10}{BOX_H}{BOX_H * 9}{BOX_H}{BOX_H * (width - 12)}{BOX_MR}")

    # Component rows
    perf_detail = f"(Grade: {player.performance_score:.0f} × Position multiplier)"
    print(f"{BOX_V} {'Perf:':<9}│ {player.performance_score:>7.1f} │ {perf_detail:<{width-21}}{BOX_V}")

    vis_detail = f"(Base 1.0x + Media/Awards/Storylines)"
    print(f"{BOX_V} {'Vis:':<9}│ {player.visibility_mult:>6.1f}x │ {vis_detail:<{width-21}}{BOX_V}")

    market_detail = f"({player.team} - Market tier)"
    print(f"{BOX_V} {'Market:':<9}│ {player.market_mult:>6.1f}x │ {market_detail:<{width-21}}{BOX_V}")

    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")

    # Calculation row
    calc = f"CALCULATION: ({player.performance_score:.1f} × {player.visibility_mult:.1f} × {player.market_mult:.1f}) = {player.popularity:.1f}"
    print(f"{BOX_V} {calc:<{width-1}}{BOX_V}")

    print(f"{BOX_BL}{BOX_H * width}{BOX_BR}")


def print_event_timeline(events: Dict[str, List[Tuple[str, str]]], week: int, use_color: bool = True):
    """Display events that occurred this week."""
    if not events:
        return

    width = 78

    print(f"{BOX_TL}{BOX_H * width}{BOX_TR}")
    print(f"{BOX_V} {'EVENT TIMELINE - Week ' + str(week):<{width-1}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")

    for player_name, player_events in events.items():
        # Player header
        print(f"{BOX_V} {player_name:<{width-1}}{BOX_V}")

        # Events
        for event_type, event_desc in player_events:
            emoji = get_event_emoji(event_type)
            event_line = f"  {emoji} {event_type}: {event_desc}"
            print(f"{BOX_V}   {event_line:<{width-3}}{BOX_V}")

        print(f"{BOX_V}{' ' * width}{BOX_V}")

    print(f"{BOX_BL}{BOX_H * width}{BOX_BR}")
    print()


def print_comparison_table(players: List[MockPlayer], week: int):
    """Display before/after comparison table."""
    width = 78

    # Filter to players with changes
    changed_players = [p for p in players if abs(p.change) > 0.5]

    if not changed_players:
        return

    print(f"{BOX_TL}{BOX_H * width}{BOX_TR}")
    print(f"{BOX_V} {'WEEK ' + str(week) + ' CHANGES':<{width-1}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")

    # Header
    header = f" {'Player':<25} │ {'Before':>6} │ {'After':>6} │ {'Change':>7} │ {'Tier':<12} │ {'Trend':<6}"
    print(f"{BOX_V}{header:<{width}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * 26}{BOX_H}{BOX_H * 8}{BOX_H}{BOX_H * 8}{BOX_H}{BOX_H * 9}{BOX_H}{BOX_H * 13}{BOX_H}{BOX_H * (width - 67)}{BOX_MR}")

    # Rows
    for p in changed_players:
        before = p.history[-2] if len(p.history) >= 2 else p.history[0]
        after = p.popularity
        change = p.change

        change_str = f"{change:+.1f}" if change != 0 else "0.0"
        trend_symbol = get_trend_symbol(p.trend)

        tier_symbol = {
            PopularityTier.TRANSCENDENT: "⭐",
            PopularityTier.STAR: "✨",
            PopularityTier.KNOWN: "✓",
            PopularityTier.ROLE_PLAYER: "·",
            PopularityTier.UNKNOWN: "○",
        }.get(p.tier, "·")

        row = f" {p.name.split('(')[0].strip():<25} │ {before:>6.1f} │ {after:>6.1f} │ {change_str:>7} │ {tier_symbol} {p.tier.value:<10} │ {trend_symbol:<6}"
        print(f"{BOX_V}{row:<{width}}{BOX_V}")

    print(f"{BOX_BL}{BOX_H * width}{BOX_BR}")
    print()


def print_summary_statistics(players: List[MockPlayer]):
    """Display summary statistics."""
    print_header("SUMMARY STATISTICS")

    # Tier distribution
    tier_counts = {}
    for tier in PopularityTier:
        tier_counts[tier] = sum(1 for p in players if p.tier == tier)

    print("Tier Distribution:")
    for tier in [PopularityTier.TRANSCENDENT, PopularityTier.STAR, PopularityTier.KNOWN,
                 PopularityTier.ROLE_PLAYER, PopularityTier.UNKNOWN]:
        count = tier_counts[tier]
        if count > 0:
            tier_symbol = {
                PopularityTier.TRANSCENDENT: "⭐",
                PopularityTier.STAR: "✨",
                PopularityTier.KNOWN: "✓",
                PopularityTier.ROLE_PLAYER: "·",
                PopularityTier.UNKNOWN: "○",
            }.get(tier, "·")

            player_names = [p.name.split('(')[1].split(')')[0] for p in players if p.tier == tier]
            print(f"  {tier_symbol} {tier.value:<15} ({tier.value.split('_')[0][0]}{tier.value.split('_')[-1][0] if '_' in tier.value else tier.value[:2]}): {count} player(s)")
            if player_names:
                print(f"      {', '.join(player_names)}")

    print()

    # Biggest gainers
    gainers = sorted([(p, p.history[-1] - p.history[0]) for p in players],
                     key=lambda x: x[1], reverse=True)[:3]

    if gainers and gainers[0][1] > 0:
        print("Biggest Gainers:")
        for i, (player, gain) in enumerate(gainers, 1):
            if gain > 0:
                name = player.name.split('(')[1].split(')')[0]
                print(f"  {i}. {name}: +{gain:.1f} points ({player.history[0]:.1f} → {player.history[-1]:.1f})")

    print()

    # Biggest losers
    losers = sorted([(p, p.history[-1] - p.history[0]) for p in players],
                    key=lambda x: x[1])[:3]

    if losers and losers[0][1] < 0:
        print("Biggest Losers:")
        for i, (player, loss) in enumerate(losers, 1):
            if loss < 0:
                name = player.name.split('(')[1].split(')')[0]
                print(f"  {i}. {name}: {loss:.1f} points ({player.history[0]:.1f} → {player.history[-1]:.1f})")

    print()

    # Average weekly change
    total_change = sum(p.history[-1] - p.history[0] for p in players)
    avg_change = total_change / len(players) if players else 0

    print(f"Total Players Tracked: {len(players)}")
    print(f"Average Total Change: {avg_change:+.1f} points")
    print()


def run_scenario_mode(args):
    """Run mock scenario simulations."""
    # Initialize players
    all_players = create_scenario_players()

    # Filter by scenario if specific one requested
    if args.scenario != 'all':
        scenario_map = {
            'breakout': ['Player A (Trevor Lawrence)'],
            'injury': ['Player B (Ezekiel Elliott)'],
            'trade': ['Player C (DJ Moore)'],
            'mvp': ['Player D (Patrick Mahomes)'],
            'playoff': ['Player E (Nick Foles)'],
            'ceiling': ['Player F (Josh Allen)'],
        }

        player_names = scenario_map.get(args.scenario, [])
        players = [p for p in all_players if p.name in player_names]
    else:
        players = all_players[:args.players]

    # Display header
    print()
    print("=" * 80)
    print("                    PLAYER POPULARITY SYSTEM DEMO")
    print("=" * 80)
    print()

    # Show formula
    print_formula_display()

    # Display initial state
    print_header("INITIAL STATE - Week 1")
    for player in players:
        print_player_card(player, week=1, use_color=not args.no_color)
        print()

    # Determine week range based on scenario
    max_week = args.weeks
    if args.scenario == 'playoff':
        max_week = 22  # Include Super Bowl

    # Simulate weeks with events
    for week in range(2, max_week + 1):
        # Get events for this week
        events = generate_events_for_week(week, args.scenario)

        # Calculate new popularity
        changes_this_week = []
        for player in players:
            player_events = events.get(player.name, [])
            old_pop = player.popularity
            new_pop = calculate_mock_popularity(player, player_events)
            player.update_week(new_pop, week)

            if player_events:
                changes_this_week.append(player.name)

        # Display changes if any events occurred
        if events:
            print_subheader(f"Week {week}")
            print_event_timeline(events, week, use_color=not args.no_color)
            print_comparison_table(players, week)

            # Show detailed card for players with major changes
            if args.verbose:
                for player in players:
                    if player.name in changes_this_week:
                        print_player_card(player, week, use_color=not args.no_color)
                        print()

                input("\nPress Enter to continue...")

    # Display final summary
    print_header("FINAL STATE - Week " + str(max_week))
    for player in players:
        print_player_card(player, week=max_week, use_color=not args.no_color)
        print()

    print_summary_statistics(players)


def main():
    """Main demo entry point."""
    parser = argparse.ArgumentParser(
        description="Player Popularity System Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python demos/popularity_demo.py                         # All 6 scenarios
    python demos/popularity_demo.py --scenario breakout     # Single scenario
    python demos/popularity_demo.py --players 3             # Limit to 3 players
    python demos/popularity_demo.py --weeks 10              # Simulate 10 weeks
    python demos/popularity_demo.py --verbose               # Step through interactively
    python demos/popularity_demo.py --no-color              # Plain text (CI/CD)

Scenarios:
    breakout - Rookie QB rises from role player to star
    injury   - Veteran RB declines during IR stint
    trade    - WR navigates market transition
    mvp      - QB reaches transcendent tier
    playoff  - Backup QB becomes legend overnight
    ceiling  - Elite LB hits small market visibility cap
    all      - Show all 6 scenarios (default)
        """
    )

    parser.add_argument(
        '--scenario',
        choices=['all', 'breakout', 'injury', 'trade', 'mvp', 'playoff', 'ceiling'],
        default='all',
        help='Scenario to run (default: all)'
    )
    parser.add_argument(
        '--players',
        type=int,
        default=6,
        help='Number of players to track (default: 6)'
    )
    parser.add_argument(
        '--weeks',
        type=int,
        default=18,
        help='Weeks to simulate (default: 18)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed cards after each event week'
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable Unicode symbols for plain text output'
    )

    args = parser.parse_args()

    # Run scenario mode
    run_scenario_mode(args)

    print()
    print("=" * 80)
    print("                           DEMO COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
