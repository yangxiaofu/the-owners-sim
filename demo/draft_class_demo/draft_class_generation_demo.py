#!/usr/bin/env python3
"""
Draft Class Generation Demo

Demonstrates the complete draft class workflow:
- Generate realistic 224-player draft classes (7 rounds × 32 picks)
- View top prospects and positional rankings
- Execute draft selections
- Track drafted players in roster
- Verify unified player_id system
- Query draft history

Usage:
    PYTHONPATH=src python demo/draft_class_demo/draft_class_generation_demo.py
"""

import sys
import tempfile
import sqlite3
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from database.draft_class_api import DraftClassAPI
from database.player_roster_api import PlayerRosterAPI
from database.dynasty_state_api import DynastyStateAPI
from database.connection import DatabaseConnection

# Import player generation system
from player_generation.generators.player_generator import PlayerGenerator
from player_generation.generators.draft_class_generator import DraftClassGenerator
from player_generation.archetypes.archetype_registry import ArchetypeRegistry

# Import archetype system to load test archetypes
# NOTE: This demo uses the same archetype loading pattern as player_generator_demo
import importlib.util
spec = importlib.util.spec_from_file_location(
    "demo_archetypes",
    Path(__file__).parent.parent / "player_generator_demo" / "player_generator_demo.py"
)
demo_archetypes_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_archetypes_module)
create_demo_archetypes = demo_archetypes_module.create_demo_archetypes


# Global archetype registry for demo
_DEMO_REGISTRY = None


def get_demo_registry():
    """Get or create demo archetype registry."""
    global _DEMO_REGISTRY
    if _DEMO_REGISTRY is None:
        _DEMO_REGISTRY = create_demo_archetypes()
    return _DEMO_REGISTRY


class DraftClassAPIDemoWrapper(DraftClassAPI):
    """Wrapper that injects demo archetypes into draft class generation."""

    def generate_draft_class(self, dynasty_id: str, season: int) -> int:
        """Generate draft class using demo archetypes."""
        # Check if draft class already exists
        if self.dynasty_has_draft_class(dynasty_id, season):
            raise ValueError(
                f"Draft class already exists for dynasty '{dynasty_id}', season {season}. "
                f"Delete existing draft class first to regenerate."
            )

        self.logger.info(f"Generating draft class for dynasty '{dynasty_id}', season {season}...")

        try:
            # Use demo archetypes
            registry = get_demo_registry()
            player_gen = PlayerGenerator(registry=registry)
            draft_gen = DraftClassGenerator(player_gen)
            generated_prospects = draft_gen.generate_draft_class(year=season)

            # Create draft class record (rest is same as parent class)
            draft_class_id = f"DRAFT_{dynasty_id}_{season}"
            from datetime import datetime
            generation_date = datetime.now()

            with sqlite3.connect(self.database_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # Insert draft class metadata
                conn.execute('''
                    INSERT INTO draft_classes (
                        draft_class_id, dynasty_id, season,
                        generation_date, total_prospects, status
                    ) VALUES (?, ?, ?, ?, ?, 'active')
                ''', (draft_class_id, dynasty_id, season, generation_date, len(generated_prospects)))

                # Insert all prospects
                for prospect in generated_prospects:
                    # Generate unique player_id using PlayerRosterAPI
                    player_id = self.player_api._get_next_player_id(dynasty_id)

                    # Insert prospect
                    self._insert_prospect(player_id, prospect, draft_class_id, dynasty_id, conn)

                conn.commit()

            self.logger.info(
                f"✅ Draft class generation complete: {len(generated_prospects)} prospects created"
            )

            return len(generated_prospects)

        except Exception as e:
            self.logger.error(f"Draft class generation failed: {e}")
            raise RuntimeError(f"Failed to generate draft class: {e}")


def print_separator(char="=", length=80):
    """Print visual separator."""
    print("\n" + char * length)


def print_header(title: str):
    """Print formatted section header."""
    print_separator("=")
    print(f"  {title}")
    print_separator("=")


def print_subheader(title: str):
    """Print formatted subsection header."""
    print_separator("-", 80)
    print(f"  {title}")
    print_separator("-", 80)


def print_prospect_row(rank: int, prospect: dict, show_draft_info: bool = False):
    """Print formatted prospect row."""
    name = f"{prospect['first_name']} {prospect['last_name']}"
    position = prospect['position']
    overall = prospect['overall']
    player_id = prospect['player_id']

    if show_draft_info and prospect.get('is_drafted'):
        team_id = prospect.get('drafted_by_team_id', 'N/A')
        round_num = prospect.get('drafted_round', 'N/A')
        pick_num = prospect.get('drafted_pick', 'N/A')
        print(f"{rank:3d}. {name:<25} {position:<6} OVR: {overall:2d}  ID: {player_id:5d}  → Team {team_id} (R{round_num}, Pick {pick_num})")
    else:
        college = prospect.get('college', 'Unknown')[:20]
        print(f"{rank:3d}. {name:<25} {position:<6} OVR: {overall:2d}  ID: {player_id:5d}  ({college})")


def print_player_card(prospect: dict):
    """Print detailed player card."""
    name = f"{prospect['first_name']} {prospect['last_name']}"

    print(f"\n┌─ {name} ".ljust(79, "─") + "┐")
    print(f"│ Player ID: {prospect['player_id']:<10} Position: {prospect['position']:<6} Age: {prospect['age']:<3}".ljust(79) + "│")
    print(f"│ Overall: {prospect['overall']:<3} Projected: {prospect['projected_pick_min']}-{prospect['projected_pick_max']}".ljust(79) + "│")
    print(f"│ College: {prospect.get('college', 'Unknown'):<40}".ljust(79) + "│")
    print(f"│ Archetype: {prospect.get('archetype_id', 'N/A'):<40}".ljust(79) + "│")

    if prospect.get('is_drafted'):
        print(f"│ ".ljust(79) + "│")
        print(f"│ DRAFTED:".ljust(79) + "│")
        print(f"│   Team: {prospect['drafted_by_team_id']}".ljust(79) + "│")
        print(f"│   Round {prospect['drafted_round']}, Pick {prospect['drafted_pick']}".ljust(79) + "│")

    print("└" + "─" * 78 + "┘")


def demo_1_generate_draft_class(draft_api: DraftClassAPI, dynasty_id: str, season: int):
    """Demo 1: Generate complete draft class."""
    print_header("DEMO 1: Generate Draft Class")

    print(f"\nGenerating draft class for dynasty '{dynasty_id}', season {season}...")
    print("⏳ Creating 224 prospects (7 rounds × 32 picks)...\n")

    # Generate draft class
    total_prospects = draft_api.generate_draft_class(dynasty_id, season)

    print(f"✅ Draft class generation complete!")
    print(f"   Total prospects created: {total_prospects}")

    # Get draft class info
    draft_info = draft_api.get_draft_class_info(dynasty_id, season)
    print(f"\nDraft Class Info:")
    print(f"   ID: {draft_info['draft_class_id']}")
    print(f"   Season: {draft_info['season']}")
    print(f"   Status: {draft_info['status']}")
    print(f"   Generated: {draft_info['generation_date']}")


def demo_2_top_prospects(draft_api: DraftClassAPI, dynasty_id: str, season: int):
    """Demo 2: Display top 32 prospects (1st round)."""
    print_header("DEMO 2: Top 32 Overall Prospects (1st Round)")

    print("\nTop prospects by overall rating (typical 1st round selections):\n")

    top_prospects = draft_api.get_top_prospects(dynasty_id, season, limit=32)

    for rank, prospect in enumerate(top_prospects, 1):
        print_prospect_row(rank, prospect)

    # Show statistics
    overalls = [p['overall'] for p in top_prospects]
    avg_overall = sum(overalls) / len(overalls)

    print(f"\nTop 32 Statistics:")
    print(f"   Average Overall: {avg_overall:.1f}")
    print(f"   Range: {min(overalls)} - {max(overalls)}")
    print(f"   Elite (85+): {len([o for o in overalls if o >= 85])} players")


def demo_3_position_filter(draft_api: DraftClassAPI, dynasty_id: str, season: int):
    """Demo 3: Filter prospects by position (QBs)."""
    print_header("DEMO 3: Position Filter - All Quarterbacks")

    print("\nAll available QB prospects in draft class:\n")

    qb_prospects = draft_api.get_prospects_by_position(dynasty_id, season, "QB", available_only=True)

    for rank, prospect in enumerate(qb_prospects, 1):
        print_prospect_row(rank, prospect)

    # Show QB statistics
    if qb_prospects:
        overalls = [p['overall'] for p in qb_prospects]
        avg_overall = sum(overalls) / len(overalls)

        print(f"\nQB Draft Class Statistics:")
        print(f"   Total QBs: {len(qb_prospects)}")
        print(f"   Average Overall: {avg_overall:.1f}")
        print(f"   Range: {min(overalls)} - {max(overalls)}")
        print(f"   First-round caliber (80+): {len([o for o in overalls if o >= 80])} QBs")


def demo_4_draft_selections(
    draft_api: DraftClassAPI,
    player_api: PlayerRosterAPI,
    dynasty_id: str,
    season: int
):
    """Demo 4: Simulate 5 draft picks."""
    print_header("DEMO 4: Execute Draft Selections")

    print("\nSimulating first 5 picks of the draft...\n")

    # Get top 10 prospects to choose from
    top_prospects = draft_api.get_top_prospects(dynasty_id, season, limit=10)

    print("Available prospects:")
    for rank, prospect in enumerate(top_prospects[:10], 1):
        print_prospect_row(rank, prospect)

    print_subheader("Executing Draft Picks")

    # Simulate 5 draft picks (teams 1-5 pick top 5 prospects)
    draft_picks = []
    for pick_num in range(1, 6):
        prospect = top_prospects[pick_num - 1]
        team_id = pick_num  # Team 1 gets pick 1, Team 2 gets pick 2, etc.

        # Mark as drafted
        draft_api.mark_prospect_drafted(
            player_id=prospect['player_id'],
            team_id=team_id,
            actual_round=1,
            actual_pick=pick_num,
            dynasty_id=dynasty_id
        )

        # Convert to player on roster
        player_id = draft_api.convert_prospect_to_player(
            player_id=prospect['player_id'],
            team_id=team_id,
            dynasty_id=dynasty_id
        )

        draft_picks.append({
            'pick': pick_num,
            'team_id': team_id,
            'player_id': player_id,
            'name': f"{prospect['first_name']} {prospect['last_name']}",
            'position': prospect['position'],
            'overall': prospect['overall']
        })

        print(f"\nPick {pick_num}: Team {team_id} selects...")
        print(f"   {draft_picks[-1]['name']} ({draft_picks[-1]['position']}, Overall: {draft_picks[-1]['overall']})")
        print(f"   ✅ Player ID {player_id} added to Team {team_id} roster")

    return draft_picks


def demo_5_drafted_players(player_api: PlayerRosterAPI, dynasty_id: str, draft_picks: list):
    """Demo 5: Show drafted players now in roster."""
    print_header("DEMO 5: Drafted Players in Team Rosters")

    print("\nVerifying drafted players appear in players table:\n")

    for pick in draft_picks:
        team_id = pick['team_id']
        player_id = pick['player_id']

        # Get player from roster
        players = player_api.get_team_players(dynasty_id, team_id)

        # Find this specific player
        player = next((p for p in players if p['player_id'] == player_id), None)

        if player:
            name = f"{player['first_name']} {player['last_name']}"
            position = player['positions'][0] if player['positions'] else 'N/A'
            jersey = player.get('number', 'N/A')

            print(f"✅ Team {team_id} Roster - #{jersey:<3} {name:<25} {position:<6} (Player ID: {player_id})")
        else:
            print(f"❌ Player ID {player_id} NOT FOUND in Team {team_id} roster!")

    print("\n✅ All drafted players successfully added to team rosters!")


def demo_6_draft_history(draft_api: DraftClassAPI, dynasty_id: str, draft_picks: list):
    """Demo 6: Query draft history for drafted players."""
    print_header("DEMO 6: Draft History Lookup")

    print("\nQuerying draft history using unified player_id:\n")

    for pick in draft_picks:
        player_id = pick['player_id']

        # Get prospect history
        history = draft_api.get_prospect_history(player_id, dynasty_id)

        if history:
            name = f"{history['first_name']} {history['last_name']}"

            print(f"\nPlayer ID {player_id}: {name}")
            print(f"   Position: {history['position']}")
            print(f"   College: {history.get('college', 'Unknown')}")
            print(f"   True Overall: {history['overall']}")
            print(f"   Projected: Picks {history['projected_pick_min']}-{history['projected_pick_max']}")
            print(f"   Drafted By: Team {history['drafted_by_team_id']}")
            print(f"   Round {history['drafted_round']}, Pick {history['drafted_pick']}")
            print(f"   Draft Class: {history['season']}")
        else:
            print(f"❌ No draft history found for Player ID {player_id}")


def demo_7_verify_id_consistency(
    draft_api: DraftClassAPI,
    player_api: PlayerRosterAPI,
    dynasty_id: str,
    draft_picks: list
):
    """Demo 7: Verify player_id consistency across tables."""
    print_header("DEMO 7: Verify Unified Player ID System")

    print("\nVerifying same player_id exists in both draft_prospects and players tables:\n")
    print("Player ID | Draft Prospects | Players Table | Match")
    print("-" * 80)

    all_match = True

    for pick in draft_picks:
        player_id = pick['player_id']

        # Check draft_prospects table
        prospect = draft_api.get_prospect_by_id(player_id, dynasty_id)
        in_prospects = prospect is not None

        # Check players table
        team_players = player_api.get_team_players(dynasty_id, pick['team_id'])
        in_players = any(p['player_id'] == player_id for p in team_players)

        match = "✅" if (in_prospects and in_players) else "❌"

        print(f"{player_id:9d} | {str(in_prospects):15} | {str(in_players):13} | {match}")

        if not (in_prospects and in_players):
            all_match = False

    print("\n" + "=" * 80)

    if all_match:
        print("✅ SUCCESS: All player IDs are consistent across tables!")
        print("   The unified player_id system is working correctly.")
    else:
        print("❌ ERROR: Some player IDs are inconsistent!")


def run_all_demos():
    """Run all demos in sequence."""
    print_separator("=")
    print("  NFL DRAFT CLASS GENERATION SYSTEM - COMPLETE DEMO")
    print_separator("=")
    print("\n  This demo showcases:")
    print("    • Generate 224-player draft class (7 rounds × 32 picks)")
    print("    • View top prospects and positional rankings")
    print("    • Execute draft selections")
    print("    • Track drafted players in team rosters")
    print("    • Query draft history")
    print("    • Verify unified player_id system")
    print_separator("=")

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_db.name
    temp_db.close()

    print(f"\nUsing temporary database: {db_path}")

    # Initialize database schema
    print("Initializing database schema...")
    db_conn = DatabaseConnection(db_path)
    db_conn.initialize_database()
    print("✅ Database schema initialized")

    # Initialize APIs (use demo wrapper for draft class generation)
    draft_api = DraftClassAPIDemoWrapper(db_path)
    player_api = PlayerRosterAPI(db_path)
    dynasty_api = DynastyStateAPI(db_path)

    # Create test dynasty
    dynasty_id = "demo_dynasty_2026"
    season = 2026

    print(f"\nCreating test dynasty: '{dynasty_id}'")

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name)
            VALUES (?, ?, ?)
        """, (dynasty_id, "Demo Dynasty 2026", "Demo User"))
        conn.commit()

    print(f"✅ Dynasty '{dynasty_id}' created\n")

    # Run demos
    demo_1_generate_draft_class(draft_api, dynasty_id, season)

    input("\n[Press ENTER to continue to Demo 2...]")
    demo_2_top_prospects(draft_api, dynasty_id, season)

    input("\n[Press ENTER to continue to Demo 3...]")
    demo_3_position_filter(draft_api, dynasty_id, season)

    input("\n[Press ENTER to continue to Demo 4...]")
    draft_picks = demo_4_draft_selections(draft_api, player_api, dynasty_id, season)

    input("\n[Press ENTER to continue to Demo 5...]")
    demo_5_drafted_players(player_api, dynasty_id, draft_picks)

    input("\n[Press ENTER to continue to Demo 6...]")
    demo_6_draft_history(draft_api, dynasty_id, draft_picks)

    input("\n[Press ENTER to continue to Demo 7...]")
    demo_7_verify_id_consistency(draft_api, player_api, dynasty_id, draft_picks)

    # Cleanup
    print_separator("=")
    print("  DEMO COMPLETE")
    print_separator("=")
    print(f"\n✅ All demos completed successfully!")
    print(f"\nTemporary database created at: {db_path}")
    print(f"You can inspect it with: sqlite3 {db_path}")
    print(f"\nTo clean up, delete the file when done:")
    print(f"  rm {db_path}")


def main():
    """Main entry point."""
    try:
        run_all_demos()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
