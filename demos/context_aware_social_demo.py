"""
Context-Aware Social Media Demo

Demonstrates how TeamContext affects social post generation across different scenarios.

Usage:
    PYTHONPATH=src python demos/context_aware_social_demo.py

Shows:
- Team context (record, playoff position, recent activity)
- Generated social posts with explanations
- How context filtering prevents hallucinations
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.services.team_context_builder import TeamContextBuilder, TeamContext, PlayoffPosition, SeasonPhase
from game_cycle.services.social_generators.game_generator import GameSocialGenerator
from game_cycle.services.post_template_loader import PostTemplateLoader
from game_cycle.models.social_event_types import SocialEventType
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from team_management.teams.team_loader import get_team_by_id


# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")


def print_section(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'-' * len(text)}{Colors.ENDC}")


def print_context(context: TeamContext, team_name: str):
    """Pretty print team context."""
    print(f"\n{Colors.BOLD}Team:{Colors.ENDC} {team_name}")
    print(f"{Colors.BOLD}Record:{Colors.ENDC} {context.get_record_string()} ({context.win_pct:.3f})")

    # Playoff status with color
    playoff_color = {
        PlayoffPosition.CLINCHED: Colors.GREEN,
        PlayoffPosition.IN_HUNT: Colors.YELLOW,
        PlayoffPosition.ELIMINATED: Colors.RED,
        PlayoffPosition.LEADER: Colors.GREEN,
        PlayoffPosition.UNKNOWN: Colors.BLUE,
    }.get(context.playoff_position, Colors.ENDC)

    print(f"{Colors.BOLD}Playoff Status:{Colors.ENDC} {playoff_color}{context.playoff_position.value}{Colors.ENDC}")
    print(f"{Colors.BOLD}Season Phase:{Colors.ENDC} {context.season_phase.value} (Week {context.week})")
    print(f"{Colors.BOLD}Division Rank:{Colors.ENDC} {context.division_rank}/4")
    print(f"{Colors.BOLD}Conference Rank:{Colors.ENDC} {context.conference_rank}/16")

    # Streak
    if context.current_streak != 0:
        streak_color = Colors.GREEN if context.streak_type == 'W' else Colors.RED
        print(f"{Colors.BOLD}Streak:{Colors.ENDC} {streak_color}{context.streak_type}{abs(context.current_streak)}{Colors.ENDC}")

    # Recent activity
    if context.recent_trades or context.recent_signings or context.recent_cuts:
        print(f"\n{Colors.BOLD}Recent Activity (last 2 weeks):{Colors.ENDC}")
        if context.recent_trades:
            print(f"  • {Colors.YELLOW}Trades:{Colors.ENDC} {len(context.recent_trades)}")
        if context.recent_signings:
            print(f"  • {Colors.GREEN}Signings:{Colors.ENDC} {len(context.recent_signings)}")
        if context.recent_cuts:
            print(f"  • {Colors.RED}Cuts:{Colors.ENDC} {len(context.recent_cuts)}")
    else:
        print(f"\n{Colors.BOLD}Recent Activity:{Colors.ENDC} None (last 2 weeks)")


def print_post(post_text: str, archetype: str, personality_name: str, explanation: str = None):
    """Pretty print a social post."""
    print(f"\n  {Colors.BOLD}{personality_name}{Colors.ENDC} ({Colors.CYAN}{archetype}{Colors.ENDC}):")
    print(f"  {Colors.BLUE}→{Colors.ENDC} \"{post_text}\"")
    if explanation:
        print(f"    {Colors.YELLOW}└─{Colors.ENDC} {explanation}")


def create_mock_context(
    team_id: int,
    team_name: str,
    wins: int,
    losses: int,
    week: int,
    playoff_position: PlayoffPosition,
    recent_trades: int = 0,
    recent_signings: int = 0,
    streak: int = 0,
    streak_type: str = 'W'
) -> TeamContext:
    """Create a mock TeamContext for demonstration."""
    total_games = wins + losses
    win_pct = wins / total_games if total_games > 0 else 0.0

    # Determine season phase
    if week <= 6:
        phase = SeasonPhase.EARLY
    elif week <= 12:
        phase = SeasonPhase.MID
    elif week <= 18:
        phase = SeasonPhase.LATE
    else:
        phase = SeasonPhase.PLAYOFFS

    # Estimate division/conference rank based on win%
    if win_pct >= 0.750:
        div_rank, conf_rank = 1, 2
    elif win_pct >= 0.625:
        div_rank, conf_rank = 2, 6
    elif win_pct >= 0.500:
        div_rank, conf_rank = 2, 10
    else:
        div_rank, conf_rank = 4, 14

    # Create mock activity dicts
    mock_trades = [{'trade_id': i, 'type': 'TRADE'} for i in range(recent_trades)]
    mock_signings = [{'player_id': i, 'type': 'FA_SIGNING'} for i in range(recent_signings)]

    return TeamContext(
        team_id=team_id,
        team_name=team_name,
        season=2025,
        week=week,
        wins=wins,
        losses=losses,
        ties=0,
        win_pct=win_pct,
        division_rank=div_rank,
        conference_rank=conf_rank,
        playoff_position=playoff_position,
        season_phase=phase,
        recent_trades=mock_trades,
        recent_signings=mock_signings,
        recent_cuts=[],
        current_streak=streak,
        streak_type=streak_type
    )


def generate_sample_posts(
    context: TeamContext,
    event_outcome: str,
    loader: PostTemplateLoader
) -> List[Dict[str, str]]:
    """Generate sample posts for different archetypes."""

    archetypes = [
        ('OPTIMIST', 'Always Believin\' Bill'),
        ('PESSIMIST', 'Doom & Gloom Dave'),
        ('BANDWAGON', 'Fairweather Fan'),
        ('BALANCED', 'Reasonable Rachel'),
    ]

    # Add trade analyst if team has recent trades
    if context.recent_trades:
        archetypes.append(('TRADE_ANALYST', 'Trade Expert Ted'))

    posts = []
    for archetype, name in archetypes:
        try:
            template = loader.get_template(
                event_type='GAME_RESULT',
                archetype=archetype,
                personality_id=1,
                event_outcome=event_outcome,
                team_context=context
            )

            # Fill template with mock data
            filled = template.replace('{winner}', 'Chiefs').replace('{loser}', 'Raiders')
            filled = filled.replace('{score}', '31-17').replace('{player}', 'Patrick Mahomes')
            filled = filled.replace('{stat}', '350 yards, 3 TDs')

            posts.append({
                'text': filled,
                'archetype': archetype,
                'name': name
            })
        except Exception as e:
            posts.append({
                'text': f"[Error: {str(e)}]",
                'archetype': archetype,
                'name': name
            })

    return posts


def run_scenario(
    scenario_name: str,
    context: TeamContext,
    team_name: str,
    event_outcome: str,
    explanation: str
):
    """Run a single scenario demo."""
    print_header(f"SCENARIO: {scenario_name}")

    print(f"{Colors.BOLD}Situation:{Colors.ENDC} {explanation}\n")

    print_section("Team Context")
    print_context(context, team_name)

    print_section(f"Generated Posts ({event_outcome.upper()})")

    loader = PostTemplateLoader()
    posts = generate_sample_posts(context, event_outcome, loader)

    for post in posts:
        # Determine if template was filtered
        has_trade = 'trade' in post['text'].lower() or 'acquisition' in post['text'].lower()
        has_playoff = 'playoff' in post['text'].lower() or 'postseason' in post['text'].lower()
        has_tank = 'draft pick' in post['text'].lower() or 'next year' in post['text'].lower()

        explanation_parts = []

        # Trade filtering
        if post['archetype'] == 'TRADE_ANALYST':
            if context.recent_trades and has_trade:
                explanation_parts.append(f"{Colors.GREEN}✓ Trade template allowed (recent trades exist){Colors.ENDC}")
            elif not context.recent_trades and has_trade:
                explanation_parts.append(f"{Colors.RED}✗ ERROR: Trade hallucination!{Colors.ENDC}")
            elif not context.recent_trades and not has_trade:
                explanation_parts.append(f"{Colors.GREEN}✓ Fell back to generic (no recent trades){Colors.ENDC}")

        # Playoff filtering
        if has_playoff:
            if context.playoff_position in [PlayoffPosition.CLINCHED, PlayoffPosition.IN_HUNT, PlayoffPosition.LEADER]:
                explanation_parts.append(f"{Colors.GREEN}✓ Playoff talk appropriate{Colors.ENDC}")
            else:
                explanation_parts.append(f"{Colors.RED}✗ ERROR: Playoff talk for eliminated team!{Colors.ENDC}")

        # Tank filtering
        if has_tank:
            if context.playoff_position == PlayoffPosition.ELIMINATED and context.week >= 12:
                explanation_parts.append(f"{Colors.GREEN}✓ Tank talk appropriate (eliminated, late season){Colors.ENDC}")
            else:
                explanation_parts.append(f"{Colors.RED}✗ ERROR: Premature tank talk!{Colors.ENDC}")

        print_post(
            post['text'],
            post['archetype'],
            post['name'],
            ' '.join(explanation_parts) if explanation_parts else None
        )


def main():
    """Run all demo scenarios."""

    print_header("CONTEXT-AWARE SOCIAL MEDIA DEMO")
    print(f"{Colors.BOLD}This demo shows how TeamContext prevents hallucinations{Colors.ENDC}")
    print(f"and ensures contextually appropriate social media posts.\n")

    # Scenario 1: Playoff Contender
    scenario_1 = create_mock_context(
        team_id=14,
        team_name="Kansas City Chiefs",
        wins=10,
        losses=3,
        week=15,
        playoff_position=PlayoffPosition.IN_HUNT,
        recent_trades=0,
        streak=3,
        streak_type='W'
    )
    run_scenario(
        "Playoff Contender (Week 15)",
        scenario_1,
        "Kansas City Chiefs",
        "WIN",
        "Team is 10-3 with a 3-game win streak, firmly in playoff hunt. "
        "NO recent trades. Should get playoff-appropriate messaging, NO trade talk."
    )

    input(f"\n{Colors.BOLD}Press Enter to continue to next scenario...{Colors.ENDC}")

    # Scenario 2: Eliminated Team
    scenario_2 = create_mock_context(
        team_id=13,
        team_name="Las Vegas Raiders",
        wins=3,
        losses=11,
        week=16,
        playoff_position=PlayoffPosition.ELIMINATED,
        recent_trades=0,
        streak=4,
        streak_type='L'
    )
    run_scenario(
        "Eliminated Team (Week 16)",
        scenario_2,
        "Las Vegas Raiders",
        "LOSS",
        "Team is 3-11 with a 4-game losing streak, eliminated from playoffs. "
        "NO recent trades. Should get 'building for next year' messaging, NO playoff talk."
    )

    input(f"\n{Colors.BOLD}Press Enter to continue to next scenario...{Colors.ENDC}")

    # Scenario 3: Recent Trade Activity
    scenario_3 = create_mock_context(
        team_id=4,
        team_name="New York Jets",
        wins=7,
        losses=6,
        week=13,
        playoff_position=PlayoffPosition.IN_HUNT,
        recent_trades=2,
        recent_signings=1,
        streak=1,
        streak_type='W'
    )
    run_scenario(
        "Active Trade Deadline Team (Week 13)",
        scenario_3,
        "New York Jets",
        "WIN",
        "Team is 7-6 in playoff hunt. Made 2 trades and 1 signing in the last 2 weeks (trade deadline). "
        "Should allow trade-related templates."
    )

    input(f"\n{Colors.BOLD}Press Enter to continue to next scenario...{Colors.ENDC}")

    # Scenario 4: Early Season
    scenario_4 = create_mock_context(
        team_id=16,
        team_name="Denver Broncos",
        wins=1,
        losses=2,
        week=3,
        playoff_position=PlayoffPosition.UNKNOWN,
        recent_trades=0,
        streak=2,
        streak_type='L'
    )
    run_scenario(
        "Early Season Struggles (Week 3)",
        scenario_4,
        "Denver Broncos",
        "LOSS",
        "Team is 1-2 early in the season with a 2-game losing streak. "
        "Too early for playoff/tank talk. Should get measured, patient messaging."
    )

    input(f"\n{Colors.BOLD}Press Enter to continue to next scenario...{Colors.ENDC}")

    # Scenario 5: Division Leader
    scenario_5 = create_mock_context(
        team_id=32,
        team_name="San Francisco 49ers",
        wins=12,
        losses=2,
        week=16,
        playoff_position=PlayoffPosition.LEADER,
        recent_trades=0,
        streak=5,
        streak_type='W'
    )
    run_scenario(
        "Division Leader (Week 16)",
        scenario_5,
        "San Francisco 49ers",
        "WIN",
        "Team is 12-2, leading the division with a 5-game win streak. "
        "Should get championship-caliber messaging."
    )

    # Final summary
    print_header("DEMO COMPLETE")
    print(f"{Colors.BOLD}Key Takeaways:{Colors.ENDC}\n")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Playoff teams get playoff messaging")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Eliminated teams get 'building for next year' messaging (late season)")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Trade templates ONLY appear when team has recent trades")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Early season has measured, patient messaging")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Context prevents hallucinations and inappropriate messaging\n")

    print(f"{Colors.BOLD}No more:{Colors.ENDC}")
    print(f"  {Colors.RED}✗{Colors.ENDC} Trade talk without trades")
    print(f"  {Colors.RED}✗{Colors.ENDC} 'Playoff bound!' for 3-11 teams")
    print(f"  {Colors.RED}✗{Colors.ENDC} 'Tank mode' talk in week 3")
    print(f"  {Colors.RED}✗{Colors.ENDC} Contextually inappropriate posts\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
