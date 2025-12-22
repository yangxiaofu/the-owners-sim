"""
Trading View Demo - Isolation test for Executive Memo style trade proposals.

Provides fast UI iteration (~1 second startup) with mock data scenarios.
No database required.

Usage:
    python demos/trading_view_demo.py              # Default scenario
    python demos/trading_view_demo.py win_now      # Win-now scenario
    python demos/trading_view_demo.py rebuild      # Rebuild scenario
    python demos/trading_view_demo.py edge_cases   # Stress test
"""

import sys
from typing import List, Dict, Any

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Slot

# Import the redesigned TradingView
from game_cycle_ui.views.trading_view import TradingView


def create_mock_proposals(scenario: str = "default") -> List[Dict[str, Any]]:
    """Generate mock trade proposal data for different scenarios."""

    if scenario == "default":
        return [
            {
                "proposal_id": "trade_001",
                "priority": "HIGH",
                "title": "Acquire Cornerback Depth",
                "trade_partner": "Los Angeles Rams",
                "confidence": 0.82,
                "sending": [
                    {"type": "pick", "year": 2026, "round": 3, "team": "Detroit Lions", "value": 150}
                ],
                "receiving": [
                    {
                        "type": "player",
                        "name": "Marcus Johnson",
                        "position": "CB",
                        "overall": 78,
                        "age": 26,
                        "cap_hit": 3200000,
                        "value": 270
                    }
                ],
                "value_differential": 120,
                "cap_impact": -3200000,
                "gm_reasoning": (
                    "Our secondary ranks 28th in pass defense and we've allowed 4+ TD passes "
                    "in 3 of our last 5 games. Johnson provides immediate slot coverage help "
                    "and fits our zone scheme perfectly. His age (26) aligns with our "
                    "competitive window."
                ),
                "strategic_fit": [
                    "Addresses #1 defensive weakness",
                    "3-year window aligns with QB contract",
                    "Minimal cap impact ($3.2M/yr)"
                ],
                "status": "PENDING"
            },
            {
                "proposal_id": "trade_002",
                "priority": "MEDIUM",
                "title": "Shop Veteran DE for Draft Capital",
                "trade_partner": "Miami Dolphins",
                "confidence": 0.68,
                "sending": [
                    {
                        "type": "player",
                        "name": "Andre Williams",
                        "position": "DE",
                        "overall": 81,
                        "age": 31,
                        "cap_hit": 8500000,
                        "value": 220
                    }
                ],
                "receiving": [
                    {"type": "pick", "year": 2026, "round": 2, "team": "Miami Dolphins", "value": 320},
                    {"type": "pick", "year": 2027, "round": 5, "team": "Miami Dolphins", "value": 40}
                ],
                "value_differential": 140,
                "cap_impact": 8500000,
                "gm_reasoning": (
                    "Williams is entering the final year of his contract and unlikely to re-sign "
                    "given his age and our cap situation. We can recoup significant draft capital "
                    "now rather than losing him to free agency. Miami is in win-now mode and "
                    "needs edge rush help."
                ),
                "strategic_fit": [
                    "Clear $8.5M in cap space",
                    "Acquire 2026 2nd round pick",
                    "Avoid losing player to free agency"
                ],
                "status": "PENDING"
            },
            {
                "proposal_id": "trade_003",
                "priority": "MEDIUM",
                "title": "Upgrade Offensive Line",
                "trade_partner": "Indianapolis Colts",
                "confidence": 0.73,
                "sending": [
                    {"type": "pick", "year": 2026, "round": 4, "team": "Detroit Lions", "value": 80},
                    {
                        "type": "player",
                        "name": "James Peterson",
                        "position": "LB",
                        "overall": 74,
                        "age": 24,
                        "cap_hit": 1200000,
                        "value": 140
                    }
                ],
                "receiving": [
                    {
                        "type": "player",
                        "name": "Michael Torres",
                        "position": "RG",
                        "overall": 79,
                        "age": 27,
                        "cap_hit": 4100000,
                        "value": 240
                    }
                ],
                "value_differential": 20,
                "cap_impact": -2900000,
                "gm_reasoning": (
                    "Our offensive line ranks 22nd in pass protection and our QB has been sacked "
                    "18 times in 8 games. Torres is a proven pass blocker who would immediately "
                    "upgrade our interior line. Peterson is expendable given our LB depth."
                ),
                "strategic_fit": [
                    "Improves QB protection immediately",
                    "Torres has 2 years left on affordable contract",
                    "Peterson is 4th on depth chart"
                ],
                "status": "PENDING"
            }
        ]

    elif scenario == "win_now":
        return [
            {
                "proposal_id": "trade_wn_001",
                "priority": "HIGH",
                "title": "Acquire Star Pass Rusher",
                "trade_partner": "Chicago Bears",
                "confidence": 0.92,
                "sending": [
                    {"type": "pick", "year": 2026, "round": 1, "team": "Detroit Lions", "value": 600},
                    {"type": "pick", "year": 2026, "round": 3, "team": "Detroit Lions", "value": 150},
                    {"type": "pick", "year": 2027, "round": 2, "team": "Detroit Lions", "value": 320}
                ],
                "receiving": [
                    {
                        "type": "player",
                        "name": "Kevin Miller",
                        "position": "EDGE",
                        "overall": 88,
                        "age": 27,
                        "cap_hit": 12500000,
                        "value": 1120
                    }
                ],
                "value_differential": 50,
                "cap_impact": -12500000,
                "gm_reasoning": (
                    "We're 7-1 and legitimate Super Bowl contenders, but our pass rush ranks "
                    "30th in the league. Miller is an elite edge rusher in his prime who can "
                    "transform our defense. This is our championship window - we must capitalize."
                ),
                "strategic_fit": [
                    "Elite talent at position of need",
                    "Proven playoff performer (6 sacks in 4 playoff games)",
                    "2 years of team control remaining"
                ],
                "status": "PENDING"
            },
            {
                "proposal_id": "trade_wn_002",
                "priority": "HIGH",
                "title": "Add WR1 for Playoff Push",
                "trade_partner": "New York Giants",
                "confidence": 0.85,
                "sending": [
                    {"type": "pick", "year": 2026, "round": 2, "team": "Detroit Lions", "value": 320},
                    {
                        "type": "player",
                        "name": "Robert Hayes",
                        "position": "WR",
                        "overall": 75,
                        "age": 23,
                        "cap_hit": 1800000,
                        "value": 180
                    }
                ],
                "receiving": [
                    {
                        "type": "player",
                        "name": "Tyler Washington",
                        "position": "WR",
                        "overall": 84,
                        "age": 29,
                        "cap_hit": 9200000,
                        "value": 520
                    }
                ],
                "value_differential": 20,
                "cap_impact": -7400000,
                "gm_reasoning": (
                    "Our receiving corps lacks a true #1 option. Washington is a proven "
                    "playmaker with excellent chemistry potential with our QB. The Giants "
                    "are rebuilding and willing to move veterans for picks."
                ),
                "strategic_fit": [
                    "Addresses red zone inefficiency (21st in TD%)",
                    "Proven 1,000+ yard receiver",
                    "Veteran leadership for young WR room"
                ],
                "status": "PENDING"
            }
        ]

    elif scenario == "rebuild":
        return [
            {
                "proposal_id": "trade_rb_001",
                "priority": "HIGH",
                "title": "Trade Star QB for Draft Haul",
                "trade_partner": "Las Vegas Raiders",
                "confidence": 0.78,
                "sending": [
                    {
                        "type": "player",
                        "name": "Derek Harrison",
                        "position": "QB",
                        "overall": 86,
                        "age": 30,
                        "cap_hit": 28500000,
                        "value": 980
                    }
                ],
                "receiving": [
                    {"type": "pick", "year": 2026, "round": 1, "team": "Las Vegas Raiders", "value": 600},
                    {"type": "pick", "year": 2027, "round": 1, "team": "Las Vegas Raiders", "value": 600},
                    {"type": "pick", "year": 2026, "round": 2, "team": "Las Vegas Raiders", "value": 320}
                ],
                "value_differential": -460,
                "cap_impact": 28500000,
                "gm_reasoning": (
                    "At 2-6, we're out of playoff contention and Harrison's value will never be "
                    "higher. This trade nets us three premium picks to rebuild around. We can "
                    "clear $28.5M in cap space and target a QB in next year's loaded draft class."
                ),
                "strategic_fit": [
                    "Two future 1st round picks for franchise rebuild",
                    "Massive cap relief ($28.5M)",
                    "Position for top QB in 2026 draft"
                ],
                "status": "PENDING"
            },
            {
                "proposal_id": "trade_rb_002",
                "priority": "MEDIUM",
                "title": "Move Aging All-Pro OT",
                "trade_partner": "Buffalo Bills",
                "confidence": 0.71,
                "sending": [
                    {
                        "type": "player",
                        "name": "Marcus Thompson",
                        "position": "LT",
                        "overall": 89,
                        "age": 33,
                        "cap_hit": 16200000,
                        "value": 550
                    }
                ],
                "receiving": [
                    {"type": "pick", "year": 2026, "round": 1, "team": "Buffalo Bills", "value": 600},
                    {"type": "pick", "year": 2027, "round": 3, "team": "Buffalo Bills", "value": 150}
                ],
                "value_differential": 200,
                "cap_impact": 16200000,
                "gm_reasoning": (
                    "Thompson is a future Hall of Famer but at 33, he doesn't fit our rebuild "
                    "timeline. Buffalo is in win-now mode after losing their starting LT. "
                    "We get another 1st rounder and clear significant cap space."
                ),
                "strategic_fit": [
                    "Acquire another 1st round pick",
                    "Clear $16.2M for young talent",
                    "Thompson won't be here for next competitive window"
                ],
                "status": "PENDING"
            },
            {
                "proposal_id": "trade_rb_003",
                "priority": "MEDIUM",
                "title": "Flip RB for Future Picks",
                "trade_partner": "Philadelphia Eagles",
                "confidence": 0.66,
                "sending": [
                    {
                        "type": "player",
                        "name": "Jordan Davis",
                        "position": "RB",
                        "overall": 82,
                        "age": 26,
                        "cap_hit": 5100000,
                        "value": 320
                    }
                ],
                "receiving": [
                    {"type": "pick", "year": 2026, "round": 3, "team": "Philadelphia Eagles", "value": 150},
                    {"type": "pick", "year": 2027, "round": 3, "team": "Philadelphia Eagles", "value": 150}
                ],
                "value_differential": -20,
                "cap_impact": 5100000,
                "gm_reasoning": (
                    "Davis is a solid RB but expendable in a rebuild. Eagles need RB depth for "
                    "playoff push after injuries. We accumulate more draft capital for the future."
                ),
                "strategic_fit": [
                    "Acquire two 3rd round picks",
                    "RB value depreciates quickly",
                    "Clear roster spot for young RBs to develop"
                ],
                "status": "PENDING"
            }
        ]

    elif scenario == "edge_cases":
        # Stress test: Many proposals, long text, extreme values
        proposals = []

        # 1. Very long GM reasoning
        proposals.append({
            "proposal_id": "trade_ec_001",
            "priority": "HIGH",
            "title": "Complex Multi-Team Trade Scenario",
            "trade_partner": "Arizona Cardinals",
            "confidence": 0.91,
            "sending": [
                {"type": "pick", "year": 2026, "round": 1, "team": "Detroit Lions", "value": 600},
                {"type": "pick", "year": 2026, "round": 2, "team": "Detroit Lions", "value": 320}
            ],
            "receiving": [
                {
                    "type": "player",
                    "name": "Christopher Rodriguez-Martinez III",
                    "position": "QB",
                    "overall": 91,
                    "age": 25,
                    "cap_hit": 8900000,
                    "value": 1200
                }
            ],
            "value_differential": 280,
            "cap_impact": -8900000,
            "gm_reasoning": (
                "This is an extremely detailed justification that goes into great depth about "
                "the strategic reasoning behind this trade proposal. Our current quarterback "
                "situation has been problematic for the past three seasons, and we've cycled "
                "through multiple veteran stopgaps without finding a long-term solution. "
                "Rodriguez-Martinez represents a generational talent who fell to the Cardinals "
                "in last year's draft due to a shoulder injury that has since fully healed. "
                "Medical reports from three independent specialists confirm 100% recovery. "
                "His college tape shows elite pocket presence, exceptional arm strength (can "
                "make every NFL throw), elite decision-making under pressure, and natural "
                "leadership qualities. The Cardinals are willing to move him because they "
                "committed to their current QB and need to rebuild other positions. This "
                "is a rare opportunity to acquire a franchise quarterback without using a "
                "top-5 pick. Our scouting department has him graded as a top-10 QB prospect "
                "in the last decade. The cost is steep (1st and 2nd round picks) but the "
                "value proposition is exceptional. His rookie contract provides 3 more years "
                "of cost control, allowing us to build around him. This single move could "
                "define our franchise for the next 15 years."
            ),
            "strategic_fit": [
                "Solves QB position for next 10-15 years",
                "Rookie contract provides 3 years of cap flexibility",
                "Elite leadership and intangibles",
                "Medical clearance from three independent specialists",
                "Scouting grade: Top-10 QB prospect in last decade"
            ],
            "status": "PENDING"
        })

        # 2-10. Multiple medium priority trades
        for i in range(2, 11):
            proposals.append({
                "proposal_id": f"trade_ec_{i:03d}",
                "priority": "MEDIUM" if i % 2 == 0 else "LOW",
                "title": f"Trade Proposal #{i}",
                "trade_partner": ["Miami Dolphins", "New England Patriots", "Buffalo Bills",
                                "Baltimore Ravens", "Cincinnati Bengals", "Cleveland Browns",
                                "Pittsburgh Steelers", "Houston Texans", "Jacksonville Jaguars"][i % 9],
                "confidence": 0.55 + (i * 0.02),
                "sending": [
                    {"type": "pick", "year": 2026, "round": 3 + (i % 3), "team": "Detroit Lions",
                     "value": 150 - (i * 10)}
                ],
                "receiving": [
                    {
                        "type": "player",
                        "name": f"Player {i}",
                        "position": ["CB", "LB", "S", "WR", "TE"][i % 5],
                        "overall": 70 + i,
                        "age": 23 + (i % 8),
                        "cap_hit": 2000000 + (i * 500000),
                        "value": 180 + (i * 10)
                    }
                ],
                "value_differential": 30 + (i * 5),
                "cap_impact": -(2000000 + (i * 500000)),
                "gm_reasoning": f"Standard depth addition at position {i}. Fills roster need.",
                "strategic_fit": [
                    "Adds depth to position group",
                    "Affordable contract",
                    "Young player with upside"
                ],
                "status": "PENDING"
            })

        # 11. Extremely unfavorable trade
        proposals.append({
            "proposal_id": "trade_ec_011",
            "priority": "LOW",
            "title": "Questionable Value Trade",
            "trade_partner": "Seattle Seahawks",
            "confidence": 0.42,
            "sending": [
                {"type": "pick", "year": 2026, "round": 1, "team": "Detroit Lions", "value": 600},
                {"type": "pick", "year": 2026, "round": 2, "team": "Detroit Lions", "value": 320}
            ],
            "receiving": [
                {
                    "type": "player",
                    "name": "Aging Veteran",
                    "position": "FS",
                    "overall": 76,
                    "age": 34,
                    "cap_hit": 11200000,
                    "value": 180
                }
            ],
            "value_differential": -740,
            "cap_impact": -11200000,
            "gm_reasoning": (
                "This trade doesn't look great on paper, but trust me on this one..."
            ),
            "strategic_fit": [
                "Veteran leadership???",
                "Experience in big games"
            ],
            "status": "PENDING"
        })

        return proposals

    else:
        # Unknown scenario, return empty
        return []


def main():
    """Main demo entry point."""
    app = QApplication(sys.argv)

    # Parse CLI args
    scenario = sys.argv[1] if len(sys.argv) > 1 else "default"

    if scenario not in ["default", "win_now", "rebuild", "edge_cases"]:
        print(f"Unknown scenario: {scenario}")
        print("Available scenarios: default, win_now, rebuild, edge_cases")
        sys.exit(1)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle(f"Trading View Demo - {scenario.title().replace('_', ' ')} Scenario")
    window.resize(1200, 800)

    # Create TradingView with mock context
    view = TradingView()
    view.set_context(
        dynasty_id="mock_dynasty",
        db_path=":memory:",
        season=2025,
        team_id=22  # Detroit Lions
    )

    # Load mock proposals
    proposals = create_mock_proposals(scenario)
    print(f"[DEMO] Loaded {len(proposals)} proposals for '{scenario}' scenario")
    view.set_gm_proposals(proposals)

    # Wire up signal handlers for demo
    @Slot(str)
    def on_proposal_approved(proposal_id: str):
        print(f"[DEMO] ✓ Approved proposal: {proposal_id}")
        # In production, this would update backend
        # For demo, we just log

    @Slot(str)
    def on_proposal_rejected(proposal_id: str):
        print(f"[DEMO] ✗ Rejected proposal: {proposal_id}")
        # In production, this would update backend
        # For demo, we just log

    view.proposal_approved.connect(on_proposal_approved)
    view.proposal_rejected.connect(on_proposal_rejected)

    # Set as central widget and show
    window.setCentralWidget(view)
    window.show()

    print("[DEMO] Window displayed. Test approve/reject buttons to see signal output.")
    print("[DEMO] Close window or Ctrl+C to exit.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
